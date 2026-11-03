"""Check codes for the verification fallback call.

Pure aside from reading CODE_PEPPER. The caller passes `now` and, when a
code must be chosen, an rng. This module does not log codes. The only
plaintext it hands back is from `generate_one_time` and `issue_one_time`,
for the in-memory holder the product design keeps for at most five minutes.
`repr` hides that plaintext.

`hash_code` / `verify_code` are the 4-digit static code: an argon2id PHC
string of pepper + code with the per-member salt. `hash_one_time` /
`verify_one_time` are the 6-digit code: HMAC-SHA256 keyed with the same
pepper, compared with `hmac.compare_digest`. Those four functions do not
look at expiry, single-use, or the lock.

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
    """Plaintext for process memory, plus the hash and expiry to store."""

    code: str = field(repr=False)
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


def generate_one_time(*, now: datetime, rng=None) -> OneTimeCode:
    """One 6-digit code for the case that just entered `calling`.

    `rng` returns an int in 0..999999. The default is `secrets.randbelow`.
    The plaintext is on the returned object and is omitted from `repr`.
    """
    _require_aware(now, "now")
    number = _draw_code(rng)
    code = f"{number:06d}"
    return OneTimeCode(code, hash_one_time(code), now + _ONE_TIME_TTL)


def issue_one_time(case: dict, *, now: datetime, rng=None) -> OneTimeCode | None:
    """Issue a code only when this case is in `calling` on the one-time channel.

    Push answers and static calls get nothing. Call this once per transition
    into that state; a second call is a different code.
    """
    _require_aware(now, "now")
    if case.get("state") != "calling" or case.get("code_channel") != "one_time":
        return None
    return generate_one_time(now=now, rng=rng)


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


def _draw_code(rng) -> int:
    if rng is None:
        return secrets.randbelow(1_000_000)
    number = rng()
    if type(number) is not int or not 0 <= number < 1_000_000:
        raise ValueError("rng must return an int in 0..999999")
    return number


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
