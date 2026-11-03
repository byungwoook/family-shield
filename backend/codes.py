"""Check codes for the verification fallback call.

Pure aside from reading CODE_PEPPER and OTP_DERIVATION_KEY. The caller
passes `now` and, when a nonce or a salt must be chosen, an rng. This
module does not log codes and does not keep a one-time code.

`hash_code` / `verify_code` are the 4-digit static code: an argon2id PHC
string of pepper + code with the per-member salt. `hash_one_time` /
`verify_one_time` are the 6-digit code: HMAC-SHA256 keyed with the same
pepper, compared with `hmac.compare_digest`. Those four functions do not
look at expiry, single-use, or the lock. Keypad verification keeps using
them against the stored hash. Expiry and single-use stay on the case row.

`derive_one_time` rebuilds those 6 digits from the case id and the per-case
nonce. The key is OTP_DERIVATION_KEY, not CODE_PEPPER, and it is not stored.
The digest is reduced with rejection sampling so every 6-digit string is
equally likely. RFC 4226 dynamic truncation then `mod 10**6` is not used:
a 31-bit integer is not divisible by 1_000_000, so that modulo is biased.

`submission_event` is the caller those columns belong to. It returns an
event `backend.verify.apply` already understands, and it does not call
`apply` itself. `static_code_locked` is the 24-hour rule that turns static
mismatch timestamps into the `static_locked` flag.
"""

import base64
import hashlib
import hmac
import os
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

from argon2.exceptions import (
    InvalidHashError,
    UnsupportedParametersError,
    VerificationError,
    VerifyMismatchError,
)
from argon2.low_level import Type, hash_secret, verify_secret


# OWASP argon2id minimum (t=2, m=19 MiB, p=1). The doc does not pin cost
# parameters; these stay inside the 4-second code_check_slow budget.
_TIME_COST = 2
_MEMORY_COST = 19456
_PARALLELISM = 1
_HASH_LEN = 32
_SALT_LEN = 16
_LOCK_LIMIT = 5
_LOCK_WINDOW = timedelta(hours=24)
_ONE_TIME_TTL = timedelta(minutes=5)
_NONCE_LEN = 16
# Largest multiple of 1_000_000 that fits in an HMAC-SHA256 digest.
# Digests at or above this limit are the biased tail and are discarded.
_DIGIT_SPACE = 1_000_000
_DIGIT_LIMIT = ((1 << 256) // _DIGIT_SPACE) * _DIGIT_SPACE
_FOUR_DIGITS = re.compile(r"[0-9]{4}")
_SIX_DIGITS = re.compile(r"[0-9]{6}")
_VERIFY_ERRORS = (
    VerifyMismatchError,
    VerificationError,
    InvalidHashError,
    UnsupportedParametersError,
    UnicodeError,
)


class CodeConfigError(RuntimeError):
    """CODE_PEPPER is unset, empty, or whitespace."""


class DerivationKeyError(RuntimeError):
    """OTP_DERIVATION_KEY is unset, empty, or whitespace."""


class BiometricRequired(Exception):
    """A replacement static code was refused: biometric_ok was not set."""


@dataclass(frozen=True)
class StaticCode:
    """Stored static check code. The plaintext is not a field."""

    code_hash: str = field(repr=False)
    salt: bytes = field(repr=False)
    code_set_at: datetime


@dataclass(frozen=True)
class OneTimeCode:
    """Nonce and hash to store. The digits are not a field."""

    nonce: bytes = field(repr=False)
    code_hash: str = field(repr=False)
    expires_at: datetime


@dataclass(frozen=True)
class OneTimeChallenge:
    """The columns the caller already stored. No plaintext."""

    code_hash: str
    expires_at: datetime
    used_at: datetime | None = None


@dataclass(frozen=True)
class Submission:
    """What to do with a keypad submission.

    `event` is `code_accepted`, `code_rejected`, `use_static_code`, or None
    when the caller must not call apply. `timeline_step` is
    `static_code_mismatch`, `code_did_not_match`, `one_time_code_expired`,
    or None. `counts_as_static_mismatch` is the 24-hour lock. A one-time
    miss does not set it. `mark_one_time_used` is set only when the one-time
    code matched and is still live.
    """

    event: str | None
    timeline_step: str | None
    counts_as_static_mismatch: bool
    mark_one_time_used: bool


def hash_code(code: str, salt: bytes) -> str:
    """Argon2id PHC string of pepper + code, using the caller's salt."""
    pepper = _pepper()
    if not isinstance(code, str):
        raise TypeError("code must be a str")
    if _FOUR_DIGITS.fullmatch(code) is None:
        raise ValueError("static check code must be 4 digits")
    raw = hash_secret(
        (pepper + code).encode("utf-8"),
        _require_salt(salt),
        time_cost=_TIME_COST,
        memory_cost=_MEMORY_COST,
        parallelism=_PARALLELISM,
        hash_len=_HASH_LEN,
        type=Type.ID,
    )
    return raw.decode("ascii")


def verify_code(code: str, salt: bytes, stored: str) -> bool:
    """True when the code, salt, and pepper match `stored`.

    A bad code shape or a corrupt hash is False. A salt that is not bytes
    of at least 16 bytes raises, so a bad row is not recorded as a guess.
    A missing pepper raises.
    """
    pepper = _pepper()
    if not isinstance(code, str) or _FOUR_DIGITS.fullmatch(code) is None:
        return False
    salt_bytes = _require_salt(salt)
    if not isinstance(stored, str):
        return False
    secret = (pepper + code).encode("utf-8")
    try:
        matched = verify_secret(stored.encode("ascii"), secret, Type.ID)
    except _VERIFY_ERRORS:
        matched = False
    return bool(matched and _salt_matches(stored, salt_bytes))


def hash_one_time(code: str) -> str:
    """Lowercase hex HMAC-SHA256 of the code, keyed with CODE_PEPPER."""
    pepper = _pepper()
    if not isinstance(code, str):
        raise TypeError("code must be a str")
    if _SIX_DIGITS.fullmatch(code) is None:
        raise ValueError("one-time code must be 6 digits")
    return hmac.new(
        pepper.encode("utf-8"), code.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def verify_one_time(code: str, stored: str) -> bool:
    """True when `stored` is the HMAC of this code. Expiry is not checked."""
    if not isinstance(code, str) or _SIX_DIGITS.fullmatch(code) is None:
        _pepper()
        return False
    return _consteq(hash_one_time(code), stored)


def derive_one_time(case_id, nonce: bytes) -> str:
    """The 6 digits for this case and nonce.

    The first HMAC is SHA-256(OTP_DERIVATION_KEY, case_id || nonce), with
    the case id as 16 canonical UUID bytes. The digest is an integer. If it
    is below the largest multiple of 1_000_000 that fits in 256 bits, the
    code is that integer mod 1_000_000. Otherwise the digest is in the
    biased tail, it is discarded, and the HMAC is retried over
    case_id || nonce || counter (4-byte big-endian, starting at 1).
    """
    key = _derivation_key()
    prefix = _case_id_bytes(case_id) + _require_nonce(nonce)
    counter = 0
    while counter <= 8:
        message = prefix if counter == 0 else prefix + counter.to_bytes(4, "big")
        digest = hmac.new(key.encode("utf-8"), message, hashlib.sha256).digest()
        code = _uniform_six_digits(digest)
        if code is not None:
            return code
        counter += 1
    raise RuntimeError("one-time code derivation rejected too many digests")


def generate_one_time(*, case_id, now: datetime, rng=None) -> OneTimeCode:
    """Draw a nonce and hash the digits it derives. The digits are not stored.

    `rng`, if passed, is `rng(16) -> bytes`. The default is
    `secrets.token_bytes`. The same case id and nonce always derive the
    same digits. The hash is what `verify_one_time` checks.
    """
    _require_aware(now, "now")
    nonce = _new_nonce(rng)
    code = derive_one_time(case_id, nonce)
    return OneTimeCode(nonce, hash_one_time(code), now + _ONE_TIME_TTL)


def issue_one_time(case: dict, *, now: datetime, rng=None) -> OneTimeCode | None:
    """Issue a code only when this case is in `calling` on the one-time channel.

    Push answers and static calls get nothing. `case['id']` is required
    because the digits are derived from it. Each call draws a new nonce.
    """
    _require_aware(now, "now")
    if case.get("state") != "calling" or case.get("code_channel") != "one_time":
        return None
    if "id" not in case:
        raise ValueError("case id is required to derive a one-time code")
    return generate_one_time(case_id=case["id"], now=now, rng=rng)


def set_static_code(
    code: str,
    *,
    now: datetime,
    biometric_ok: bool,
    existing_set_at: datetime | None,
    rng=None,
) -> StaticCode:
    """Store a new static code.

    The first set (`existing_set_at is None`) does not require a biometric
    flag: signup has no biometric step. A replacement does. `biometric_ok`
    must be a bool either way. `rng`, if passed, is `rng(16) -> bytes`.
    """
    if not isinstance(biometric_ok, bool):
        raise TypeError("biometric_ok must be a bool")
    if existing_set_at is not None:
        if biometric_ok is False:
            raise BiometricRequired(
                "replacing a static check code requires biometric_ok"
            )
        _require_aware(existing_set_at, "existing_set_at")
    _require_aware(now, "now")
    salt = _new_salt(rng)
    return StaticCode(hash_code(code, salt), salt, now)


def static_code_locked(
    mismatch_ats,
    *,
    code_set_at: datetime | None,
    now: datetime,
) -> bool:
    """True when five static mismatches fall in the open lock window.

    A miss counts when `code_set_at < at <= now` and `at >= now - 24 hours`.
    Misses at or before `code_set_at` do not count, which is how setting a
    new code clears the lock without deleting rows. No `code_set_at` means
    there is nothing to lock. One-time misses are not this list.
    """
    _require_aware(now, "now")
    if code_set_at is not None:
        _require_aware(code_set_at, "code_set_at")
    window_start = now - _LOCK_WINDOW
    count = 0
    for at in mismatch_ats:
        _require_aware(at, "mismatch time")
        if code_set_at is None or at <= code_set_at:
            continue
        if at < window_start or at > now:
            continue
        count += 1
    return count >= _LOCK_LIMIT


def submission_event(
    case: dict,
    digits: str,
    *,
    now: datetime,
    static: StaticCode | None = None,
    one_time: OneTimeChallenge | None = None,
) -> Submission:
    """Decide the state-machine event for one keypad submission.

    Star (`*` on either gather, or an empty string on the one-time gather)
    is `use_static_code` and is not a guess. Any other one-time submission
    that is not six live, unused digits is `code_rejected`. A static
    submission that is not the right 4-digit code is `code_rejected` and
    counts toward the lock. Outside `calling`, the submission is ignored.
    """
    _require_aware(now, "now")
    if case.get("state") != "calling":
        return _ignore()
    channel = case.get("code_channel")
    if _is_star(channel, digits):
        return Submission("use_static_code", None, False, False)
    if channel == "one_time":
        return _one_time_submission(digits, now, one_time)
    if channel == "static":
        return _static_submission(case, digits, static)
    return _reject("code_did_not_match")


def _one_time_submission(digits, now, one_time) -> Submission:
    if not isinstance(digits, str) or _SIX_DIGITS.fullmatch(digits) is None:
        return _reject("code_did_not_match")
    if one_time is None:
        _pepper()
        return _reject("code_did_not_match")
    _require_aware(one_time.expires_at, "expires_at")
    if one_time.used_at is not None:
        _require_aware(one_time.used_at, "used_at")
    matched = verify_one_time(digits, one_time.code_hash)
    if one_time.used_at is not None:
        return _reject("code_did_not_match")
    if now >= one_time.expires_at:
        return _reject("one_time_code_expired")
    if not matched:
        return _reject("code_did_not_match")
    return Submission("code_accepted", None, False, True)


def _static_submission(case, digits, static) -> Submission:
    if case["static_locked"]:
        return Submission("code_rejected", None, False, False)
    if digits == "":
        return _ignore()
    if isinstance(digits, str) and _FOUR_DIGITS.fullmatch(digits) is not None:
        if static is None:
            _pepper()
            return _reject("static_code_mismatch", static_mismatch=True)
        if verify_code(digits, static.salt, static.code_hash):
            return Submission("code_accepted", None, False, False)
        return _reject("static_code_mismatch", static_mismatch=True)
    return _reject("static_code_mismatch", static_mismatch=True)


def _is_star(channel, digits) -> bool:
    if digits == "*":
        return True
    return digits == "" and channel == "one_time"


def _reject(step: str | None, *, static_mismatch: bool = False) -> Submission:
    return Submission("code_rejected", step, static_mismatch, False)


def _ignore() -> Submission:
    return Submission(None, None, False, False)


def _pepper() -> str:
    value = os.environ.get("CODE_PEPPER")
    if value is None or value.strip() == "":
        raise CodeConfigError("CODE_PEPPER is required")
    return value


def _derivation_key() -> str:
    value = os.environ.get("OTP_DERIVATION_KEY")
    if value is None or value.strip() == "":
        raise DerivationKeyError("OTP_DERIVATION_KEY is required")
    return value


def _case_id_bytes(case_id: object) -> bytes:
    if isinstance(case_id, UUID):
        return case_id.bytes
    if isinstance(case_id, str):
        try:
            return UUID(case_id).bytes
        except ValueError:
            raise ValueError("case id must be a UUID") from None
    raise TypeError("case id must be a UUID")


def _require_nonce(nonce: object) -> bytes:
    if type(nonce) is not bytes or len(nonce) != _NONCE_LEN:
        raise ValueError("nonce must be 16 bytes")
    return nonce


def _new_nonce(rng) -> bytes:
    if rng is None:
        return secrets.token_bytes(_NONCE_LEN)
    nonce = rng(_NONCE_LEN)
    if type(nonce) is not bytes or len(nonce) != _NONCE_LEN:
        raise ValueError("nonce rng must return 16 bytes")
    return nonce


def _uniform_six_digits(digest: bytes) -> str | None:
    if len(digest) != 32:
        raise ValueError("digest must be 32 bytes")
    value = int.from_bytes(digest, "big")
    if value >= _DIGIT_LIMIT:
        return None
    return f"{value % _DIGIT_SPACE:06d}"


def _require_salt(salt: object) -> bytes:
    if not isinstance(salt, bytes) or len(salt) < _SALT_LEN:
        raise ValueError("salt must be at least 16 bytes")
    return salt


def _new_salt(rng) -> bytes:
    if rng is None:
        return secrets.token_bytes(_SALT_LEN)
    salt = rng(_SALT_LEN)
    if type(salt) is not bytes or len(salt) != _SALT_LEN:
        raise ValueError("salt rng must return 16 bytes")
    return salt


def _require_aware(value: object, label: str) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.tzinfo.utcoffset(value) is None
    ):
        raise ValueError(f"{label} must be a timezone-aware datetime")
    return value


def _consteq(expected: str, stored: object) -> bool:
    if not isinstance(stored, str) or len(stored) != len(expected):
        hmac.compare_digest(expected, expected)
        return False
    return hmac.compare_digest(expected, stored)


def _salt_matches(stored: str, salt: bytes) -> bool:
    embedded = _salt_from_phc(stored)
    if embedded is None or len(embedded) != len(salt):
        return False
    return hmac.compare_digest(embedded, salt)


def _salt_from_phc(stored: str) -> bytes | None:
    parts = stored.split("$")
    if len(parts) != 6 or parts[1] != "argon2id":
        return None
    try:
        raw = parts[4].encode("ascii")
        pad = b"=" * (-len(raw) % 4)
        return base64.b64decode(raw + pad, validate=True)
    except (ValueError, UnicodeError):
        return None
