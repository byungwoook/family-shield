"""Milestone 5: Apple and Google ID-token checks, with no network.

Readings, where the milestone text allows more than one:

- "Audience pinned" means one configured audience per provider: the iOS
  bundle id for Apple, the server client id the Android app requests the
  token for on Google. A token whose `aud` list includes it is accepted.
- Times are checked against the injected clock with a 60-second leeway.
  The tests use a clock in 2020 so a pass cannot come from the wall clock.
- Only RS256 is accepted, and only with the key the JWKS lists for that
  `kid`. A token signed with another key under the same `kid` is refused.
- The result is the provider and `sub`. Email and name are not read.
- Milestone 12: the token's `nonce` claim must equal `expected_nonce`,
  which the API computes as `nonce_claim(raw)`, the lowercase SHA-256 hex of
  the raw nonce it issued. Missing, different, or a raw value in place of
  the hash is `InvalidIdToken("nonce")`.
"""

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from backend.signin import (
    APPLE_ISSUERS,
    GOOGLE_ISSUERS,
    LEEWAY,
    Identity,
    IdTokenVerifier,
    InvalidIdToken,
    apple_verifier,
    google_verifier,
    hash_signin_nonce,
    new_signin_nonce,
    nonce_claim,
    signin_nonce_ok,
)


NOW = datetime(2020, 5, 1, 12, 0, tzinfo=timezone.utc)
APPLE_AUD = "com.example.familyshield"
GOOGLE_AUD = "1234-server.apps.googleusercontent.com"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
KEYS = {"k1": KEY.public_key()}
RAW_NONCE = "n" * 43
NONCE = nonce_claim(RAW_NONCE)


def lookup(kid):
    return KEYS[kid]


def make_token(
    *,
    iss="https://appleid.apple.com",
    aud=APPLE_AUD,
    sub="001234.abcdef.0001",
    iat=None,
    exp=None,
    kid="k1",
    key=KEY,
    alg="RS256",
    extra=None,
    drop=(),
):
    claims = {
        "iss": iss,
        "aud": aud,
        "sub": sub,
        "iat": int((NOW if iat is None else iat).timestamp()),
        "exp": int((NOW + timedelta(minutes=10) if exp is None else exp).timestamp()),
        "nonce": NONCE,
    }
    claims.update(extra or {})
    for name in drop:
        claims.pop(name, None)
    headers = {} if kid is None else {"kid": kid}
    return jwt.encode(claims, key, algorithm=alg, headers=headers)


def apple():
    return apple_verifier(APPLE_AUD, keys=lookup)


def google():
    return google_verifier(GOOGLE_AUD, keys=lookup)


def test_a_valid_apple_token_returns_the_subject():
    assert apple().verify(make_token(), now=NOW, expected_nonce=NONCE) == Identity("apple", "001234.abcdef.0001")


@pytest.mark.parametrize("issuer", sorted(GOOGLE_ISSUERS))
def test_google_accepts_both_documented_issuers(issuer):
    token = make_token(iss=issuer, aud=GOOGLE_AUD, sub="1087654321")
    assert google().verify(token, now=NOW, expected_nonce=NONCE) == Identity("google", "1087654321")


def test_the_issuer_sets_are_exact():
    assert APPLE_ISSUERS == {"https://appleid.apple.com"}
    assert GOOGLE_ISSUERS == {"https://accounts.google.com", "accounts.google.com"}


def test_an_apple_token_is_not_a_google_token():
    token = make_token(aud=GOOGLE_AUD)
    with pytest.raises(InvalidIdToken):
        google().verify(token, now=NOW, expected_nonce=NONCE)


def test_another_audience_is_refused():
    with pytest.raises(InvalidIdToken):
        apple().verify(make_token(aud="com.example.other"), now=NOW, expected_nonce=NONCE)


def test_an_audience_list_must_contain_ours():
    assert apple().verify(make_token(aud=["x", APPLE_AUD]), now=NOW, expected_nonce=NONCE).subject
    with pytest.raises(InvalidIdToken):
        apple().verify(make_token(aud=["x", "y"]), now=NOW, expected_nonce=NONCE)


def test_expiry_uses_the_injected_clock_and_a_small_leeway():
    inside = make_token(exp=NOW - LEEWAY + timedelta(seconds=1))
    assert apple().verify(inside, now=NOW, expected_nonce=NONCE).subject
    outside = make_token(exp=NOW - LEEWAY - timedelta(seconds=1))
    with pytest.raises(InvalidIdToken, match="expired"):
        apple().verify(outside, now=NOW, expected_nonce=NONCE)


def test_a_token_from_the_future_is_refused():
    token = make_token(iat=NOW + LEEWAY + timedelta(seconds=5))
    with pytest.raises(InvalidIdToken, match="issued_in_future"):
        apple().verify(token, now=NOW, expected_nonce=NONCE)


def test_not_before_in_the_future_is_refused():
    token = make_token(extra={"nbf": int((NOW + timedelta(minutes=5)).timestamp())})
    with pytest.raises(InvalidIdToken, match="not_yet_valid"):
        apple().verify(token, now=NOW, expected_nonce=NONCE)


@pytest.mark.parametrize("claim", ["iss", "aud", "sub", "exp", "iat"])
def test_a_missing_required_claim_is_refused(claim):
    with pytest.raises(InvalidIdToken):
        apple().verify(make_token(drop=(claim,)), now=NOW, expected_nonce=NONCE)


@pytest.mark.parametrize("subject", ["", "   ", " padded", "x" * 256, 12345])
def test_a_bad_subject_is_refused(subject):
    with pytest.raises(InvalidIdToken):
        apple().verify(make_token(sub=subject), now=NOW, expected_nonce=NONCE)


def test_hs256_signed_with_the_public_key_is_refused():
    pem = KEY.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    header = jwt.utils.base64url_encode(b'{"alg":"HS256","typ":"JWT","kid":"k1"}')
    body = jwt.utils.base64url_encode(
        json.dumps(
            {
                "iss": "https://appleid.apple.com",
                "aud": APPLE_AUD,
                "sub": "forged",
                "iat": int(NOW.timestamp()),
                "exp": int((NOW + timedelta(minutes=5)).timestamp()),
            }
        ).encode()
    )
    signing = header + b"." + body
    signature = jwt.utils.base64url_encode(hmac.new(pem, signing, hashlib.sha256).digest())
    token = (signing + b"." + signature).decode()
    with pytest.raises(InvalidIdToken, match="algorithm"):
        apple().verify(token, now=NOW, expected_nonce=NONCE)


def test_alg_none_is_refused():
    token = jwt.encode(
        {"iss": "https://appleid.apple.com", "aud": APPLE_AUD, "sub": "x", "iat": 1, "exp": 2},
        None,
        algorithm="none",
        headers={"kid": "k1"},
    )
    with pytest.raises(InvalidIdToken, match="algorithm"):
        apple().verify(token, now=NOW, expected_nonce=NONCE)


def test_a_different_key_under_a_known_kid_is_refused():
    with pytest.raises(InvalidIdToken, match="signature"):
        apple().verify(make_token(key=OTHER_KEY), now=NOW, expected_nonce=NONCE)


def test_an_unknown_or_missing_kid_is_refused():
    with pytest.raises(InvalidIdToken, match="kid"):
        apple().verify(make_token(kid="k2"), now=NOW, expected_nonce=NONCE)
    with pytest.raises(InvalidIdToken, match="kid"):
        apple().verify(make_token(kid=None), now=NOW, expected_nonce=NONCE)


def test_a_key_source_failure_is_a_refusal_not_a_crash():
    def broken(_kid):
        raise ConnectionError("jwks down")

    verifier = apple_verifier(APPLE_AUD, keys=broken)
    with pytest.raises(InvalidIdToken, match="kid"):
        verifier.verify(make_token(), now=NOW, expected_nonce=NONCE)


@pytest.mark.parametrize("token", ["", "abc", "a.b.c", "x" * 9000, None])
def test_malformed_tokens_are_refused(token):
    with pytest.raises(InvalidIdToken):
        apple().verify(token, now=NOW, expected_nonce=NONCE)


def test_a_naive_clock_is_a_programming_error():
    with pytest.raises(ValueError):
        apple().verify(make_token(), now=NOW.replace(tzinfo=None), expected_nonce=NONCE)


def test_the_refusal_message_never_contains_the_token():
    token = make_token(aud="com.example.other")
    with pytest.raises(InvalidIdToken) as caught:
        apple().verify(token, now=NOW, expected_nonce=NONCE)
    assert token not in str(caught.value)


def test_a_verifier_needs_an_audience_and_a_known_provider():
    with pytest.raises(ValueError):
        IdTokenVerifier(provider="apple", audience=" ", issuers=APPLE_ISSUERS, keys=lookup)
    with pytest.raises(ValueError):
        IdTokenVerifier(provider="github", audience="x", issuers=APPLE_ISSUERS, keys=lookup)


# --- Nonce (milestone 12) ---


def test_nonce_claim_is_lowercase_sha256_hex_of_the_raw_nonce():
    assert NONCE == hashlib.sha256(RAW_NONCE.encode()).hexdigest()
    assert NONCE == NONCE.lower() and len(NONCE) == 64


def test_a_token_without_a_nonce_claim_is_refused():
    with pytest.raises(InvalidIdToken, match="nonce"):
        apple().verify(make_token(drop=("nonce",)), now=NOW, expected_nonce=NONCE)


def test_a_different_nonce_is_refused():
    other = nonce_claim("m" * 43)
    with pytest.raises(InvalidIdToken, match="nonce"):
        apple().verify(make_token(), now=NOW, expected_nonce=other)
    with pytest.raises(InvalidIdToken, match="nonce"):
        google().verify(
            make_token(iss="https://accounts.google.com", aud=GOOGLE_AUD),
            now=NOW,
            expected_nonce=other,
        )


def test_the_raw_nonce_in_the_claim_is_not_the_hash():
    token = make_token(extra={"nonce": RAW_NONCE})
    with pytest.raises(InvalidIdToken, match="nonce"):
        apple().verify(token, now=NOW, expected_nonce=NONCE)
    upper = make_token(extra={"nonce": NONCE.upper()})
    with pytest.raises(InvalidIdToken, match="nonce"):
        apple().verify(upper, now=NOW, expected_nonce=NONCE)


@pytest.mark.parametrize("claim", [12345, None, ["x"]])
def test_a_non_string_nonce_claim_is_refused(claim):
    with pytest.raises(InvalidIdToken, match="nonce"):
        apple().verify(make_token(extra={"nonce": claim}), now=NOW, expected_nonce=NONCE)


@pytest.mark.parametrize("expected", ["", None])
def test_an_empty_expected_nonce_is_a_programming_error(expected):
    with pytest.raises(ValueError):
        apple().verify(make_token(), now=NOW, expected_nonce=expected)


def test_new_nonces_are_url_safe_long_and_distinct(monkeypatch):
    monkeypatch.setenv("CODE_PEPPER", "test-pepper-0123456789")
    nonces = {new_signin_nonce() for _ in range(50)}
    assert len(nonces) == 50
    for nonce in nonces:
        assert len(nonce) >= 32 and signin_nonce_ok(nonce)
        stored = hash_signin_nonce(nonce)
        assert stored != nonce and stored != nonce_claim(nonce)
        assert nonce not in stored and len(stored) == 64


@pytest.mark.parametrize("raw", ["", "short", "x" * 31, "x" * 129, "has space" + "x" * 30, None, 7])
def test_a_nonce_of_the_wrong_shape_is_not_ok(raw):
    assert not signin_nonce_ok(raw)
