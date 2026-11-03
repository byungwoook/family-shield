"""Tests for milestone 2 check codes.

The contract is docs/PRODUCT_REDESIGN.md, "M2. Check codes", and the call-code
rules under "Which code the call asks for". `hash_*` / `verify_*` only hash.
Expiry and single-use are case columns. `submission_event` is the caller that
checks them and returns a `backend.verify.apply` event.

Edges the doc leaves blank, locked in here:

- A one-time code is live while ``now < expires_at`` and dead at that instant.
- A static mismatch counts when ``code_set_at < at <= now`` and ``at >= now - 24h``.
- Star is ``*`` on either gather, and an empty string only on the one-time gather.
- Replacing a static code requires ``biometric_ok is True``. The first set does not.
- The stored one-time value is lowercase hex HMAC-SHA256, key ``CODE_PEPPER``,
  message the code.
"""

import ast
import hashlib
import hmac
import inspect
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import pytest

from backend.codes import (
    BiometricRequired,
    CodeConfigError,
    DerivationKeyError,
    OneTimeChallenge,
    OneTimeCode,
    StaticCode,
    Submission,
    derive_one_time,
    generate_one_time,
    hash_code,
    hash_one_time,
    issue_one_time,
    set_static_code,
    static_code_locked,
    submission_event,
    verify_code,
    verify_one_time,
)
from backend import codes as codes_module
from backend.verify import apply


PEPPER = "test-pepper-0123456789"
OTHER_PEPPER = "another-pepper-0123456789"
DERIVATION_KEY = "test-derivation-key-0123456789"
OTHER_DERIVATION_KEY = "other-derivation-key-0123456789"
CASE_ID = UUID("11111111-2222-3333-4444-555555555555")
NONCE = bytes(range(16))
SALT_A = bytes(range(16))
SALT_B = bytes(range(16, 32))
NOW = datetime(2026, 11, 3, 1, 0, tzinfo=timezone.utc)
CODE_SET = NOW - timedelta(hours=24)
STATIC_DIGITS = "1357"
ONE_TIME_DIGITS = "135790"


@pytest.fixture
def pepper(monkeypatch):
    monkeypatch.setenv("CODE_PEPPER", PEPPER)
    monkeypatch.setenv("OTP_DERIVATION_KEY", DERIVATION_KEY)
    return PEPPER


def nonce_rng(n):
    return b"\x11" * n


def issued_digits(issued, case_id=CASE_ID):
    return derive_one_time(case_id, issued.nonce)


@pytest.fixture
def static(pepper):
    return set_static_code(
        STATIC_DIGITS,
        now=CODE_SET,
        biometric_ok=False,
        existing_set_at=None,
        rng=lambda n: b"\x22" * n,
    )


def calling_case(**overrides):
    base = {
        "state": "calling",
        "result": None,
        "answered_via": None,
        "code_channel": "one_time",
        "has_app": True,
        "has_push_token": False,
        "has_opted_in_phone": True,
        "number_recent": False,
        "static_locked": False,
        "slow_checks": 0,
    }
    base.update(overrides)
    return base


def opened(**overrides):
    base = calling_case(state="opened", code_channel=None, has_app=False)
    base.update(overrides)
    return base


def submit(case, digits, *, now, static=None, one_time=None):
    decision = submission_event(
        case, digits, now=now, static=static, one_time=one_time
    )
    if decision.event is None:
        return case, decision
    return apply(case, decision.event), decision


def challenge(issued, *, used_at=None):
    return OneTimeChallenge(issued.code_hash, issued.expires_at, used_at)


# --- Hashing and pepper ---


def test_m2_functions_match_the_documented_signatures():
    assert list(inspect.signature(hash_code).parameters) == ["code", "salt"]
    assert list(inspect.signature(verify_code).parameters) == ["code", "salt", "stored"]
    assert list(inspect.signature(hash_one_time).parameters) == ["code"]
    assert list(inspect.signature(verify_one_time).parameters) == ["code", "stored"]
    for fn in (hash_code, verify_code, hash_one_time, verify_one_time):
        assert "pepper" not in inspect.signature(fn).parameters
        assert "now" not in inspect.signature(fn).parameters


def test_missing_pepper_raises_before_a_shape_error(monkeypatch):
    monkeypatch.delenv("CODE_PEPPER", raising=False)
    with pytest.raises(CodeConfigError):
        hash_code("12", SALT_A)
    with pytest.raises(CodeConfigError):
        verify_code("", SALT_A, "x")
    with pytest.raises(CodeConfigError):
        hash_one_time("12345")
    with pytest.raises(CodeConfigError):
        verify_one_time("12345", "abc")


@pytest.mark.parametrize("value", ["", "   ", "\n"])
def test_blank_pepper_raises(monkeypatch, value):
    monkeypatch.setenv("CODE_PEPPER", value)
    with pytest.raises(CodeConfigError) as caught:
        hash_one_time("123456")
    assert "123456" not in str(caught.value)


def test_config_error_does_not_echo_a_previous_pepper(monkeypatch):
    monkeypatch.setenv("CODE_PEPPER", PEPPER)
    monkeypatch.setenv("CODE_PEPPER", "")
    with pytest.raises(CodeConfigError) as caught:
        hash_code(STATIC_DIGITS, SALT_A)
    assert PEPPER not in str(caught.value)
    assert STATIC_DIGITS not in str(caught.value)


@pytest.mark.parametrize(
    "code",
    ["", "123", "12345", "12a4", "1234 ", " 1234", "１２３４"],
)
def test_hash_code_rejects_anything_but_four_ascii_digits(pepper, code):
    with pytest.raises(ValueError) as caught:
        hash_code(code, SALT_A)
    if code:
        assert code not in str(caught.value)


@pytest.mark.parametrize(
    "code",
    ["", "123", "12345", "12a4", "1234 ", "１２３４", None],
)
def test_verify_code_rejects_a_bad_shape_without_raising(pepper, code):
    assert verify_code(code, SALT_A, "not-a-hash") is False


def test_short_salt_raises_when_the_code_shape_is_valid(pepper):
    with pytest.raises(ValueError) as caught:
        hash_code(STATIC_DIGITS, b"\x01" * 15)
    assert STATIC_DIGITS not in str(caught.value)
    with pytest.raises(ValueError):
        verify_code(STATIC_DIGITS, b"\x01" * 15, "$argon2id$")


def test_bad_code_shape_does_not_raise_on_a_short_salt(pepper):
    assert verify_code("12", b"short", "x") is False


def test_static_hash_matches_only_the_same_code_salt_and_pepper(pepper, monkeypatch):
    stored = hash_code(STATIC_DIGITS, SALT_A)
    assert isinstance(stored, str)
    assert stored.startswith("$argon2id$")
    assert STATIC_DIGITS not in stored
    assert PEPPER not in stored
    assert hash_code(STATIC_DIGITS, SALT_A) == stored
    assert verify_code(STATIC_DIGITS, SALT_A, stored) is True
    assert verify_code("1358", SALT_A, stored) is False
    assert verify_code(STATIC_DIGITS, SALT_A, None) is False
    assert verify_code(STATIC_DIGITS, SALT_A, "not-a-phc-string") is False
    assert verify_code(None, SALT_A, stored) is False
    monkeypatch.setenv("CODE_PEPPER", OTHER_PEPPER)
    assert verify_code(STATIC_DIGITS, SALT_A, stored) is False
    assert hash_code(STATIC_DIGITS, SALT_A) != stored


def test_two_salts_of_the_same_code_do_not_verify_against_each_other(pepper):
    """Vector: code 1357, salt bytes(range(16)) versus bytes(range(16, 32))."""
    stored_a = hash_code(STATIC_DIGITS, SALT_A)
    stored_b = hash_code(STATIC_DIGITS, SALT_B)
    assert stored_a != stored_b
    assert verify_code(STATIC_DIGITS, SALT_A, stored_a) is True
    assert verify_code(STATIC_DIGITS, SALT_B, stored_b) is True
    assert verify_code(STATIC_DIGITS, SALT_B, stored_a) is False
    assert verify_code(STATIC_DIGITS, SALT_A, stored_b) is False


def test_hash_code_rejects_a_non_string(pepper):
    with pytest.raises(TypeError):
        hash_code(1357, SALT_A)


@pytest.mark.parametrize(
    "code",
    ["", "12345", "1234567", "12345a", "123456 ", "１２３４５６"],
)
def test_hash_one_time_rejects_anything_but_six_ascii_digits(pepper, code):
    with pytest.raises(ValueError) as caught:
        hash_one_time(code)
    if code:
        assert code not in str(caught.value)


@pytest.mark.parametrize(
    "code",
    ["", "12345", "1234567", "12345a", None],
)
def test_verify_one_time_bad_shape_is_false(pepper, code):
    assert verify_one_time(code, "ab" * 32) is False


def test_one_time_hash_is_hmac_sha256_with_the_pepper(pepper):
    expected = hmac.new(
        PEPPER.encode("utf-8"), ONE_TIME_DIGITS.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    stored = hash_one_time(ONE_TIME_DIGITS)
    assert stored == expected
    assert len(stored) == 64
    assert verify_one_time(ONE_TIME_DIGITS, stored) is True
    assert verify_one_time("135791", stored) is False
    assert verify_one_time(ONE_TIME_DIGITS, None) is False
    assert stored != hashlib.sha256(ONE_TIME_DIGITS.encode("utf-8")).hexdigest()


def test_verify_one_time_does_not_know_about_expiry_or_single_use(pepper):
    params = inspect.signature(verify_one_time).parameters
    assert list(params) == ["code", "stored"]
    stored = hash_one_time(ONE_TIME_DIGITS)
    assert verify_one_time(ONE_TIME_DIGITS, stored) is True


def test_hash_one_time_rejects_a_non_string(pepper):
    with pytest.raises(TypeError):
        hash_one_time(135790)


# --- Issuing a one-time code ---


def test_derive_one_time_is_hmac_rejection_sampling(pepper):
    code = derive_one_time(CASE_ID, NONCE)
    assert len(code) == 6 and code.isdigit()
    again = derive_one_time(str(CASE_ID), NONCE)
    assert again == code
    assert derive_one_time(CASE_ID, bytes(range(16, 32))) != code
    message = CASE_ID.bytes + NONCE
    digest = hmac.new(
        DERIVATION_KEY.encode("utf-8"), message, hashlib.sha256
    ).digest()
    assert code == f"{int.from_bytes(digest, 'big') % 1_000_000:06d}"


def test_derivation_key_is_not_the_pepper(pepper, monkeypatch):
    first = derive_one_time(CASE_ID, NONCE)
    monkeypatch.setenv("OTP_DERIVATION_KEY", OTHER_DERIVATION_KEY)
    assert derive_one_time(CASE_ID, NONCE) != first
    monkeypatch.setenv("OTP_DERIVATION_KEY", DERIVATION_KEY)
    monkeypatch.setenv("CODE_PEPPER", OTHER_PEPPER)
    assert derive_one_time(CASE_ID, NONCE) == first


def test_missing_derivation_key_raises(monkeypatch):
    monkeypatch.setenv("CODE_PEPPER", PEPPER)
    monkeypatch.delenv("OTP_DERIVATION_KEY", raising=False)
    with pytest.raises(DerivationKeyError) as caught:
        derive_one_time(CASE_ID, NONCE)
    assert DERIVATION_KEY not in str(caught.value)
    assert "135790" not in str(caught.value)
    monkeypatch.setenv("OTP_DERIVATION_KEY", "   ")
    with pytest.raises(DerivationKeyError):
        derive_one_time(CASE_ID, NONCE)


def test_biased_digest_is_rejected_and_retried(pepper, monkeypatch):
    limit = codes_module._DIGIT_LIMIT
    tail = limit.to_bytes(32, "big")
    good_value = limit - 1
    good = good_value.to_bytes(32, "big")
    messages = []

    class _Digest:
        def __init__(self, message):
            self.message = message

        def digest(self):
            return tail if len(messages) == 1 else good

    def fake_new(key, msg=b"", digestmod=None):
        messages.append(msg)
        return _Digest(msg)

    monkeypatch.setattr(codes_module.hmac, "new", fake_new)
    code = derive_one_time(CASE_ID, NONCE)
    assert code == f"{good_value % 1_000_000:06d}"
    assert messages[0] == CASE_ID.bytes + NONCE
    assert messages[1] == CASE_ID.bytes + NONCE + (1).to_bytes(4, "big")


def test_generate_one_time_uses_the_injected_clock_and_rng(pepper):
    issued = generate_one_time(case_id=CASE_ID, now=NOW, rng=nonce_rng)
    digits = issued_digits(issued)
    assert isinstance(issued, OneTimeCode)
    assert issued.nonce == b"\x11" * 16
    assert issued.expires_at == NOW + timedelta(minutes=5)
    assert verify_one_time(digits, issued.code_hash) is True
    assert digits not in repr(issued)
    assert digits not in str(issued)
    assert digits.encode() not in issued.nonce
    assert not hasattr(issued, "code")


def test_default_nonce_is_drawn_when_no_rng_is_passed(pepper):
    issued = generate_one_time(case_id=CASE_ID, now=NOW)
    other = generate_one_time(case_id=CASE_ID, now=NOW)
    assert len(issued.nonce) == 16
    assert other.nonce != issued.nonce
    assert verify_one_time(derive_one_time(CASE_ID, issued.nonce), issued.code_hash)


def test_nonce_rng_must_return_16_bytes(pepper):
    with pytest.raises(ValueError):
        generate_one_time(case_id=CASE_ID, now=NOW, rng=lambda n: True)
    with pytest.raises(ValueError):
        generate_one_time(case_id=CASE_ID, now=NOW, rng=lambda n: b"\x11" * 15)
    with pytest.raises(ValueError):
        generate_one_time(case_id=CASE_ID, now=NOW, rng=lambda n: b"\x11" * 17)
    with pytest.raises(ValueError):
        derive_one_time(CASE_ID, b"\x11" * 15)


def test_generate_rejects_a_naive_clock(pepper):
    with pytest.raises(ValueError):
        generate_one_time(case_id=CASE_ID, now=datetime(2026, 11, 3), rng=nonce_rng)


def test_issue_one_time_only_while_the_fallback_call_is_asking(pepper):
    asking = calling_case(id=CASE_ID)
    issued = issue_one_time(asking, now=NOW, rng=nonce_rng)
    assert issued.nonce == b"\x11" * 16
    assert verify_one_time(issued_digits(issued), issued.code_hash) is True
    assert issue_one_time(
        calling_case(code_channel="static", has_app=False), now=NOW, rng=nonce_rng
    ) is None
    assert issue_one_time(
        calling_case(state="awaiting_answer", id=CASE_ID), now=NOW, rng=nonce_rng
    ) is None
    with pytest.raises(ValueError):
        issue_one_time(calling_case(), now=NOW, rng=nonce_rng)
    with pytest.raises(ValueError):
        issue_one_time(asking, now=datetime(2026, 11, 3), rng=nonce_rng)


def test_push_answer_does_not_issue_a_code():
    waiting = apply(opened(has_app=True, has_push_token=True), "start")
    assert waiting["state"] == "waiting_push"
    assert issue_one_time(waiting, now=NOW, rng=nonce_rng) is None
    decided = apply(waiting, "push_answered_yes")
    assert decided["result"] == "sent"
    assert issue_one_time(decided, now=NOW, rng=nonce_rng) is None


def test_missed_push_issues_one_code_for_that_case(pepper):
    waiting = apply(opened(has_app=True, has_push_token=True), "start")
    calling = apply(waiting, "push_window_elapsed")
    assert calling["state"] == "calling"
    assert calling["code_channel"] == "one_time"
    issued = issue_one_time({**calling, "id": CASE_ID}, now=NOW, rng=nonce_rng)
    digits = issued_digits(issued)
    assert verify_one_time(digits, issued.code_hash) is True
    assert digits not in "".join(str(value) for value in calling.values())


def test_a_child_without_the_app_is_not_issued_a_one_time_code():
    calling = apply(opened(), "start")
    assert calling["code_channel"] == "static"
    assert issue_one_time(calling, now=NOW, rng=nonce_rng) is None


# --- Static code, biometric reset, lockout ---


def test_first_static_code_does_not_require_biometrics(pepper):
    record = set_static_code(
        "0007",
        now=CODE_SET,
        biometric_ok=False,
        existing_set_at=None,
        rng=lambda n: b"\x11" * n,
    )
    assert isinstance(record, StaticCode)
    assert record.code_set_at == CODE_SET
    assert record.salt == b"\x11" * 16
    assert "0007" not in repr(record)
    assert verify_code("0007", record.salt, record.code_hash) is True
    assert verify_code("7", record.salt, record.code_hash) is False


def test_biometric_flag_must_be_a_bool():
    with pytest.raises(TypeError):
        set_static_code(
            STATIC_DIGITS,
            now=NOW,
            biometric_ok=1,
            existing_set_at=None,
        )


def test_reset_requires_the_biometric_flag(monkeypatch):
    monkeypatch.delenv("CODE_PEPPER", raising=False)
    with pytest.raises(BiometricRequired) as caught:
        set_static_code(
            STATIC_DIGITS,
            now=NOW,
            biometric_ok=False,
            existing_set_at=CODE_SET,
        )
    assert STATIC_DIGITS not in str(caught.value)
    with pytest.raises(TypeError):
        set_static_code(
            STATIC_DIGITS,
            now=NOW,
            biometric_ok="yes",
            existing_set_at=CODE_SET,
        )


def test_reset_replaces_the_hash_and_clears_the_lock(pepper):
    old = set_static_code(
        STATIC_DIGITS,
        now=CODE_SET,
        biometric_ok=False,
        existing_set_at=None,
        rng=lambda n: b"\x11" * n,
    )
    new = set_static_code(
        STATIC_DIGITS,
        now=NOW,
        biometric_ok=True,
        existing_set_at=old.code_set_at,
        rng=lambda n: b"\x33" * n,
    )
    assert new.code_set_at == NOW
    assert new.salt != old.salt
    assert verify_code(STATIC_DIGITS, old.salt, old.code_hash) is True
    assert verify_code(STATIC_DIGITS, new.salt, new.code_hash) is True
    assert verify_code(STATIC_DIGITS, old.salt, new.code_hash) is False
    assert verify_code(STATIC_DIGITS, new.salt, old.code_hash) is False
    misses = [CODE_SET + timedelta(minutes=1)] * 5
    assert static_code_locked(misses, code_set_at=old.code_set_at, now=NOW) is True
    assert static_code_locked(misses, code_set_at=new.code_set_at, now=NOW) is False


def test_salt_rng_must_return_sixteen_bytes(pepper):
    with pytest.raises(ValueError):
        set_static_code(
            STATIC_DIGITS,
            now=NOW,
            biometric_ok=False,
            existing_set_at=None,
            rng=lambda n: b"short",
        )


def test_default_salt_is_sixteen_random_bytes(pepper):
    first = set_static_code(
        STATIC_DIGITS, now=NOW, biometric_ok=False, existing_set_at=None
    )
    second = set_static_code(
        STATIC_DIGITS, now=NOW, biometric_ok=False, existing_set_at=None
    )
    assert len(first.salt) == 16
    assert isinstance(first.salt, bytes)
    assert first.salt != second.salt


def test_five_mismatches_in_the_window_lock_and_the_boundary_does():
    code_set_at = NOW - timedelta(days=2)
    recent = [NOW - timedelta(hours=i) for i in range(4)]
    assert static_code_locked(recent, code_set_at=code_set_at, now=NOW) is False
    assert static_code_locked(
        [NOW - timedelta(hours=24), *recent], code_set_at=code_set_at, now=NOW
    ) is True
    assert static_code_locked(
        [NOW - timedelta(hours=24, microseconds=1), *recent],
        code_set_at=code_set_at,
        now=NOW,
    ) is False


def test_mismatches_at_or_before_code_set_at_do_not_count():
    code_set_at = NOW - timedelta(hours=1)
    assert static_code_locked(
        [code_set_at] * 5, code_set_at=code_set_at, now=NOW
    ) is False
    just_after = code_set_at + timedelta(microseconds=1)
    assert static_code_locked(
        [just_after] * 5, code_set_at=code_set_at, now=NOW
    ) is True


def test_no_code_set_at_is_not_locked_and_future_misses_do_not_count():
    assert static_code_locked([NOW] * 5, code_set_at=None, now=NOW) is False
    code_set_at = NOW - timedelta(days=1)
    future = [NOW + timedelta(microseconds=1)] * 5
    assert static_code_locked(future, code_set_at=code_set_at, now=NOW) is False


def test_identical_timestamps_count_separately():
    code_set_at = NOW - timedelta(hours=2)
    assert static_code_locked([NOW] * 4, code_set_at=code_set_at, now=NOW) is False
    assert static_code_locked([NOW] * 5, code_set_at=code_set_at, now=NOW) is True
    assert static_code_locked(
        (NOW for _ in range(5)), code_set_at=code_set_at, now=NOW
    ) is True


def test_naive_lock_clock_is_rejected():
    with pytest.raises(ValueError):
        static_code_locked([], code_set_at=None, now=datetime(2026, 11, 3))
    with pytest.raises(ValueError):
        static_code_locked(
            [datetime(2026, 11, 3)],
            code_set_at=NOW - timedelta(hours=1),
            now=NOW,
        )


def test_five_static_misses_block_the_next_call_without_the_app():
    misses = [NOW - timedelta(minutes=i) for i in range(5)]
    assert static_code_locked(
        misses, code_set_at=NOW - timedelta(days=2), now=NOW
    ) is True
    blocked = apply(opened(static_locked=True), "start")
    assert blocked["state"] == "not_confirmed"
    assert blocked["result"] == "code_locked"
    assert blocked["code_channel"] is None
    still_calls = apply(
        opened(static_locked=True, has_app=True),
        "start",
    )
    assert still_calls["state"] == "calling"
    assert still_calls["code_channel"] == "one_time"


# --- What a keypad submission does to the call ---


def test_star_switches_once_and_needs_no_pepper(monkeypatch):
    monkeypatch.delenv("CODE_PEPPER", raising=False)
    case = calling_case()
    switched, decision = submit(case, "*", now=NOW)
    assert decision == Submission(
        event="use_static_code",
        timeline_step=None,
        counts_as_static_mismatch=False,
        mark_one_time_used=False,
    )
    assert switched["state"] == "calling"
    assert switched["code_channel"] == "static"
    assert switched["result"] is None
    again, second = submit(switched, "*", now=NOW)
    assert second.event == "use_static_code"
    assert again is switched
    empty, empty_decision = submit(case, "", now=NOW)
    assert empty_decision.event == "use_static_code"
    assert empty["code_channel"] == "static"


def test_star_while_the_static_code_is_locked_ends_without_a_guess():
    ended, decision = submit(calling_case(static_locked=True), "*", now=NOW)
    assert decision.event == "use_static_code"
    assert decision.counts_as_static_mismatch is False
    assert ended["state"] == "not_confirmed"
    assert ended["result"] == "code_locked"
    assert ended["result"] != "wrong"


def test_wrong_static_code_ends_the_call_immediately(pepper, static):
    case = calling_case(code_channel="static", has_app=False)
    ended, decision = submit(case, "0000", now=NOW, static=static)
    assert decision.event == "code_rejected"
    assert decision.timeline_step == "static_code_mismatch"
    assert decision.counts_as_static_mismatch is True
    assert "0000" not in repr(decision)
    assert ended["state"] == "not_confirmed"
    assert ended["result"] == "wrong"
    assert ended["result"] != "not_sent"
    again, later = submit(ended, STATIC_DIGITS, now=NOW, static=static)
    assert later.event is None
    assert later.counts_as_static_mismatch is False
    assert again is ended


def test_right_static_code_asks_the_question(pepper, static):
    case = calling_case(code_channel="static", has_app=False)
    updated, decision = submit(case, STATIC_DIGITS, now=NOW, static=static)
    assert decision.event == "code_accepted"
    assert decision.counts_as_static_mismatch is False
    assert decision.mark_one_time_used is False
    assert updated["state"] == "awaiting_answer"
    assert updated["result"] is None
    assert STATIC_DIGITS not in repr(decision)


def test_star_then_the_static_code(pepper, static):
    switched, _ = submit(calling_case(), "*", now=NOW)
    assert switched["code_channel"] == "static"
    accepted, decision = submit(switched, STATIC_DIGITS, now=NOW, static=static)
    assert decision.event == "code_accepted"
    assert accepted["state"] == "awaiting_answer"
    assert accepted["code_channel"] == "static"
    ended, wrong = submit(switched, "0000", now=NOW, static=static)
    assert wrong.counts_as_static_mismatch is True
    assert ended["result"] == "wrong"


def test_empty_static_gather_is_not_an_attempt(static):
    case = calling_case(code_channel="static", has_app=False)
    same, decision = submit(case, "", now=NOW, static=static)
    assert decision.event is None
    assert decision.counts_as_static_mismatch is False
    assert same is case


def test_non_digit_static_submission_is_a_mismatch(static):
    case = calling_case(code_channel="static", has_app=False)
    ended, decision = submit(case, "12ab", now=NOW, static=static)
    assert decision.timeline_step == "static_code_mismatch"
    assert decision.counts_as_static_mismatch is True
    assert ended["result"] == "wrong"


def test_locked_static_channel_does_not_accept_the_right_code(static):
    case = calling_case(code_channel="static", has_app=False, static_locked=True)
    ended, decision = submit(case, STATIC_DIGITS, now=NOW, static=static)
    assert decision.event == "code_rejected"
    assert decision.counts_as_static_mismatch is False
    assert ended["state"] == "not_confirmed"
    assert ended["result"] == "wrong"


def test_one_time_code_expires_at_the_five_minute_mark(pepper):
    issued = generate_one_time(case_id=CASE_ID, now=NOW, rng=nonce_rng)
    digits = issued_digits(issued)
    assert issued.expires_at == NOW + timedelta(minutes=5)
    live = challenge(issued)
    case = calling_case()
    still, alive = submit(
        case,
        digits,
        now=issued.expires_at - timedelta(microseconds=1),
        one_time=live,
    )
    assert alive.event == "code_accepted"
    assert alive.mark_one_time_used is True
    assert still["state"] == "awaiting_answer"
    expired, dead = submit(case, digits, now=issued.expires_at, one_time=live)
    assert dead == Submission(
        event="code_rejected",
        timeline_step="one_time_code_expired",
        counts_as_static_mismatch=False,
        mark_one_time_used=False,
    )
    assert digits not in repr(dead)
    assert expired["state"] == "not_confirmed"
    assert expired["result"] == "wrong"
    assert expired["result"] != "not_sent"
    later, also = submit(
        case,
        digits,
        now=issued.expires_at + timedelta(microseconds=1),
        one_time=live,
    )
    assert also.timeline_step == "one_time_code_expired"
    assert later["result"] == "wrong"


def test_one_time_code_is_single_use(pepper):
    issued = generate_one_time(case_id=CASE_ID, now=NOW, rng=nonce_rng)
    digits = issued_digits(issued)
    used = challenge(issued, used_at=NOW)
    ended, decision = submit(
        calling_case(),
        digits,
        now=NOW + timedelta(seconds=30),
        one_time=used,
    )
    assert decision.event == "code_rejected"
    assert decision.timeline_step == "code_did_not_match"
    assert decision.mark_one_time_used is False
    assert decision.counts_as_static_mismatch is False
    assert ended["state"] == "not_confirmed"
    assert ended["result"] == "wrong"
    accepted = apply(calling_case(), "code_accepted")
    ignored, later = submit(
        accepted,
        digits,
        now=NOW + timedelta(seconds=30),
        one_time=used,
    )
    assert later.event is None
    assert ignored is accepted


def test_a_used_code_past_expiry_is_not_relabeled_as_expired(pepper):
    issued = generate_one_time(case_id=CASE_ID, now=NOW, rng=nonce_rng)
    used = challenge(issued, used_at=NOW)
    _, decision = submit(
        calling_case(),
        issued_digits(issued),
        now=issued.expires_at,
        one_time=used,
    )
    assert decision.timeline_step == "code_did_not_match"
    assert decision.event == "code_rejected"


def test_wrong_one_time_code_ends_the_call_and_does_not_switch(pepper):
    issued = generate_one_time(case_id=CASE_ID, now=NOW, rng=nonce_rng)
    ended, decision = submit(
        calling_case(), "000000", now=NOW, one_time=challenge(issued)
    )
    assert decision.event == "code_rejected"
    assert decision.timeline_step == "code_did_not_match"
    assert decision.counts_as_static_mismatch is False
    assert "000000" not in repr(decision)
    assert ended["state"] == "not_confirmed"
    assert ended["result"] == "wrong"
    assert ended["code_channel"] == "one_time"
    assert apply(ended, "use_static_code") is ended


def test_four_digits_on_the_one_time_gather_do_not_switch(monkeypatch):
    monkeypatch.delenv("CODE_PEPPER", raising=False)
    ended, decision = submit(calling_case(), STATIC_DIGITS, now=NOW)
    assert decision.event == "code_rejected"
    assert decision.counts_as_static_mismatch is False
    assert ended["result"] == "wrong"
    assert ended["code_channel"] == "one_time"


def test_one_time_check_fails_closed_without_a_pepper(monkeypatch):
    monkeypatch.delenv("CODE_PEPPER", raising=False)
    live = OneTimeChallenge("ab" * 32, NOW + timedelta(minutes=5))
    with pytest.raises(CodeConfigError):
        submission_event(
            calling_case(), ONE_TIME_DIGITS, now=NOW, static=None, one_time=live
        )


def test_one_time_misses_do_not_feed_the_static_lock(pepper):
    issued = generate_one_time(case_id=CASE_ID, now=NOW, rng=nonce_rng)
    recorded = []
    case = calling_case()
    for _ in range(5):
        _, decision = submit(case, "000000", now=NOW, one_time=challenge(issued))
        if decision.counts_as_static_mismatch:
            recorded.append(NOW)
    assert recorded == []
    assert static_code_locked(
        recorded, code_set_at=NOW - timedelta(days=1), now=NOW
    ) is False


def test_digits_after_the_call_moved_on_do_not_count(static):
    waiting = calling_case(state="awaiting_answer")
    same, decision = submit(waiting, "0000", now=NOW, static=static)
    assert decision.event is None
    assert decision.counts_as_static_mismatch is False
    assert decision.mark_one_time_used is False
    assert same is waiting


def test_codes_module_takes_time_and_rng_from_the_caller_and_does_not_log():
    source = Path("backend/codes.py").read_text()
    tree = ast.parse(source)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module.split(".")[0])
    banned = {"verify", "services", "logging", "requests", "time", "dotenv"}
    assert banned.isdisjoint(imported)
    assert "datetime.now" not in source
    assert "time.time" not in source
    assert "print(" not in source
    assert "hmac.compare_digest" in source
    assert "hmac.new" in source
    assert "verify_secret" in source
