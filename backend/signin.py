"""Apple and Google ID tokens. Milestone 5.

`IdTokenVerifier.verify(token, now=...)` returns the provider and the `sub`
claim, or raises `InvalidIdToken`. Nothing else in the token is trusted:
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

No nonce is checked in this milestone. A stolen ID token can be replayed
until its `exp`. Apple tokens live about 10 minutes and Google tokens an
hour. A nonce bound to the app's sign-in request is a follow-up.

`jwks_keys(url)` is the production key source. Tests pass a dict lookup.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

import jwt


APPLE_ISSUERS = frozenset({"https://appleid.apple.com"})
GOOGLE_ISSUERS = frozenset({"https://accounts.google.com", "accounts.google.com"})
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
LEEWAY = timedelta(seconds=60)
_TOKEN_LIMIT = 8192
_SUBJECT_LIMIT = 255
_ALGORITHM = "RS256"


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

    def verify(self, token: str, *, now: datetime) -> Identity:
        if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
            raise ValueError("now must be a timezone-aware datetime")
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
