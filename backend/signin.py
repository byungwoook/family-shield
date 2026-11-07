"""Apple and Google ID tokens. Milestone 5.

`IdTokenVerifier.verify(token, now=..., expected_nonce=...)` returns the
provider and the `sub` claim, or raises `InvalidIdToken`. Nothing else in the token is trusted:
email, name, and `email_verified` do not identify a family member, and the
API never looks them up.

The checks, in order:

- The header names RS256 and a `kid`. Any other algorithm, including
  `none` and HS256, is refused before a key is looked up. PyJWT is also
  given `algorithms=["RS256"]`, so a key cannot be used as an HMAC secret.
- The key for that `kid` comes from the provider's JWKS. An unknown `kid`
  is a refusal, not a fallback to another key.
- The signature, then `aud` against the one audience this deployment pins
  (Apple: the iOS bundle id. Google: the server client id the Android app
  requests the token for). `aud` as a list must contain it.
- `iss` is Apple's or Google's issuer string exactly.
- `exp`, `iat`, and `nbf` are checked against the injected clock with a
  60-second leeway, not against `time.time()`, so tests do not depend on
  the wall clock.
- `sub` is a non-empty string of at most 255 characters.

- `nonce` equals `expected_nonce` exactly (milestone 12). The app asks
  `POST /v1/auth/nonce` for a raw nonce, hands `nonce_claim(raw)` (lowercase
  SHA-256 hex) to Apple or Google as the request nonce, and posts the raw
  value with the token. The server stores only `hash_signin_nonce(raw)` and
  consumes it once, so a captured token cannot be replayed: its nonce is
  already spent, and a fresh nonce does not match the token's claim. A
  missing or different claim is `InvalidIdToken("nonce")`.

`jwks_keys(url)` is the production key source. Tests pass a dict lookup.
"""

import hashlib
import hmac
import re
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

import jwt

from backend.codes import keyed_hash


APPLE_ISSUERS = frozenset({"https://appleid.apple.com"})
GOOGLE_ISSUERS = frozenset({"https://accounts.google.com", "accounts.google.com"})
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
LEEWAY = timedelta(seconds=60)
_TOKEN_LIMIT = 8192
_SUBJECT_LIMIT = 255
_ALGORITHM = "RS256"
# The raw sign-in nonce: 32 random bytes as url-safe base64 is 43 characters.
NONCE_TTL = timedelta(minutes=10)
NONCE_LIMIT = 128
_NONCE = re.compile(r"[A-Za-z0-9_-]{32,128}")
_NONCE_DOMAIN = "signin_nonce"


class InvalidIdToken(Exception):
    """The token was not accepted. The message is a stable reason, never the token."""


@dataclass(frozen=True)
class Identity:
    provider: str
    subject: str


class IdTokenVerifier:
    def __init__(
        self,
        *,
        provider: str,
        audience: str,
        issuers: frozenset,
        keys: Callable[[str], object],
    ) -> None:
        if provider not in ("apple", "google"):
            raise ValueError("provider must be apple or google")
        if not isinstance(audience, str) or audience.strip() == "":
            raise ValueError("audience is required")
        if not issuers:
            raise ValueError("issuers are required")
        self.provider = provider
        self.audience = audience.strip()
        self.issuers = frozenset(issuers)
        self._keys = keys

    def verify(self, token: str, *, now: datetime, expected_nonce: str) -> Identity:
        if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
            raise ValueError("now must be a timezone-aware datetime")
        if not isinstance(expected_nonce, str) or expected_nonce == "":
            raise ValueError("expected_nonce is required")
        if not isinstance(token, str) or token == "" or len(token) > _TOKEN_LIMIT:
            raise InvalidIdToken("malformed")
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError:
            raise InvalidIdToken("malformed") from None
        if header.get("alg") != _ALGORITHM:
            raise InvalidIdToken("algorithm")
        kid = header.get("kid")
        if not isinstance(kid, str) or kid == "":
            raise InvalidIdToken("kid")
        try:
            key = self._keys(kid)
        except Exception:
            raise InvalidIdToken("kid") from None
        if key is None:
            raise InvalidIdToken("kid")
        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=[_ALGORITHM],
                audience=self.audience,
                options={
                    "verify_exp": False,
                    "verify_iat": False,
                    "verify_nbf": False,
                    "verify_iss": False,
                    "require": ["iss", "aud", "sub", "exp", "iat"],
                },
            )
        except jwt.PyJWTError:
            raise InvalidIdToken("signature_or_audience") from None
        if claims.get("iss") not in self.issuers:
            raise InvalidIdToken("issuer")
        at = now.timestamp()
        leeway = LEEWAY.total_seconds()
        exp = _number(claims.get("exp"))
        iat = _number(claims.get("iat"))
        nbf = claims.get("nbf")
        if exp is None or iat is None:
            raise InvalidIdToken("times")
        if at >= exp + leeway:
            raise InvalidIdToken("expired")
        if iat > at + leeway:
            raise InvalidIdToken("issued_in_future")
        if nbf is not None:
            nbf_value = _number(nbf)
            if nbf_value is None or nbf_value > at + leeway:
                raise InvalidIdToken("not_yet_valid")
        subject = claims.get("sub")
        if (
            not isinstance(subject, str)
            or subject.strip() == ""
            or subject != subject.strip()
            or len(subject) > _SUBJECT_LIMIT
        ):
            raise InvalidIdToken("subject")
        claimed = claims.get("nonce")
        if not isinstance(claimed, str) or not hmac.compare_digest(
            claimed.encode("utf-8"), expected_nonce.encode("utf-8")
        ):
            raise InvalidIdToken("nonce")
        return Identity(self.provider, subject)


def apple_verifier(audience: str, keys: Callable[[str], object] | None = None) -> IdTokenVerifier:
    return IdTokenVerifier(
        provider="apple",
        audience=audience,
        issuers=APPLE_ISSUERS,
        keys=keys if keys is not None else jwks_keys(APPLE_JWKS_URL),
    )


def google_verifier(audience: str, keys: Callable[[str], object] | None = None) -> IdTokenVerifier:
    return IdTokenVerifier(
        provider="google",
        audience=audience,
        issuers=GOOGLE_ISSUERS,
        keys=keys if keys is not None else jwks_keys(GOOGLE_JWKS_URL),
    )


def new_signin_nonce() -> str:
    """A raw sign-in nonce: 32 random bytes, url-safe base64, 43 characters."""
    return secrets.token_urlsafe(32)


def signin_nonce_ok(raw: object) -> bool:
    """True when `raw` has the shape of a nonce this server could have issued."""
    return isinstance(raw, str) and _NONCE.fullmatch(raw) is not None


def nonce_claim(raw: str) -> str:
    """What the app hands Apple or Google, and what the token's `nonce` must be."""
    if not isinstance(raw, str):
        raise TypeError("nonce must be a str")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def hash_signin_nonce(raw: str) -> str:
    """The stored form: `keyed_hash("signin_nonce", raw)`. Not the token claim."""
    return keyed_hash(_NONCE_DOMAIN, raw)


def jwks_keys(url: str) -> Callable[[str], object]:
    """A cached JWKS lookup. The first request fetches; an unknown kid refetches once."""
    client = jwt.PyJWKClient(url, cache_keys=True, lifespan=3600, timeout=5)

    def lookup(kid: str):
        return client.get_signing_key(kid).key

    return lookup


def _number(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)
