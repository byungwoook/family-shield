"""Push to the child's device: APNs or FCM. Milestone 8.

One generic alert per case. The lock screen shows it, so it says only that
Family Shield needs a confirmation: no amount, no story, no transcript, and
neither code. The data is `kind=money_request` and the case id. Tapping it
opens the app, which asks the fixed question behind a biometric check.
Sending to a token proves nothing: the answer still needs the child's session.

`send` returns `sent`, `permanent` (the token is dead: unregistered, bad, or
for another app), or `transient` (try again later; the 90-second window
falls through to the call either way). It never raises for a provider error.

- APNs: HTTP/2 with a provider token (ES256 JWT from the .p8 key, cached and
  renewed every 50 minutes). Sandbox or production host from `push_env`.
- FCM: HTTP v1 with an OAuth access token minted from the service account
  (RS256 JWT exchanged at Google's token endpoint, cached until near expiry).

Both take an injected `post` so tests never open a socket. Nothing here logs
a token, a key, or the payload.
"""

import json
import logging
import time
from collections.abc import Callable
from pathlib import Path

import jwt


log = logging.getLogger(__name__)

PUSH_TTL_SECONDS = 90
ALERT_TITLE = {"en": "Family Shield", "ko": "패밀리 쉴드"}
ALERT_BODY = {
    "en": "Family Shield needs you to confirm a request.",
    "ko": "패밀리 쉴드에서 확인이 필요한 요청이 있어요.",
}
APNS_HOSTS = {
    "production": "https://api.push.apple.com",
    "sandbox": "https://api.sandbox.push.apple.com",
}
FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_APNS_PERMANENT = frozenset(
    {"BadDeviceToken", "Unregistered", "DeviceTokenNotForTopic", "TopicDisallowed"}
)
_FCM_PERMANENT = frozenset({"UNREGISTERED", "INVALID_ARGUMENT", "SENDER_ID_MISMATCH"})


def alert_text(locale: str | None) -> tuple[str, str]:
    language = "ko" if locale == "ko" else "en"
    return ALERT_TITLE[language], ALERT_BODY[language]


def apns_payload(case_id, locale: str | None) -> dict:
    title, body = alert_text(locale)
    return {
        "aps": {"alert": {"title": title, "body": body}, "sound": "default"},
        "kind": "money_request",
        "case_id": str(case_id),
    }


def fcm_message(token: str, case_id, locale: str | None) -> dict:
    title, body = alert_text(locale)
    return {
        "message": {
            "token": token,
            "notification": {"title": title, "body": body},
            "data": {"kind": "money_request", "case_id": str(case_id)},
            "android": {"priority": "HIGH", "ttl": f"{PUSH_TTL_SECONDS}s"},
        }
    }


class RecordingPush:
    """Records each push and answers with a queued outcome (default `sent`)."""

    def __init__(self, outcomes=None) -> None:
        self.sent: list[dict] = []
        self.outcomes = list(outcomes or [])

    def send(self, *, provider, token, env, locale, case_id) -> str:
        if provider == "apns":
            payload = apns_payload(case_id, locale)
        else:
            payload = fcm_message(token, case_id, locale)
        self.sent.append(
            {"provider": provider, "token": token, "env": env, "payload": payload}
        )
        return self.outcomes.pop(0) if self.outcomes else "sent"


class ApnsSender:
    def __init__(
        self,
        *,
        team_id: str,
        key_id: str,
        private_key: str,
        topic: str,
        post: Callable | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if not (team_id and key_id and private_key and topic):
            raise ValueError("APNs needs a team id, key id, private key, and topic")
        self._team = team_id
        self._key_id = key_id
        self._key = private_key
        self._topic = topic
        self._post = post
        self._clock = clock
        self._jwt = None
        self._jwt_at = 0.0

    def _provider_token(self) -> str:
        now = self._clock()
        if self._jwt is None or now - self._jwt_at > 50 * 60:
            self._jwt = jwt.encode(
                {"iss": self._team, "iat": int(now)},
                self._key,
                algorithm="ES256",
                headers={"kid": self._key_id},
            )
            self._jwt_at = now
        return self._jwt

    def _client_post(self):
        if self._post is None:
            import httpx

            client = httpx.Client(http2=True, timeout=10)
            self._post = client.post
        return self._post

    def send(self, *, token, env, locale, case_id, **_ignored) -> str:
        host = APNS_HOSTS.get(env)
        if host is None:
            return "permanent"
        headers = {
            "authorization": f"bearer {self._provider_token()}",
            "apns-topic": self._topic,
            "apns-push-type": "alert",
            "apns-priority": "10",
            "apns-expiration": str(int(self._clock()) + PUSH_TTL_SECONDS),
        }
        try:
            response = self._client_post()(
                f"{host}/3/device/{token}",
                headers=headers,
                content=json.dumps(apns_payload(case_id, locale)).encode("utf-8"),
            )
        except Exception as exc:
            log.warning("apns send failed: %s", type(exc).__name__)
            return "transient"
        status = getattr(response, "status_code", None)
        if status == 200:
            return "sent"
        reason = _json_field(response, "reason")
        if status == 410 or reason in _APNS_PERMANENT:
            return "permanent"
        log.warning("apns status %s %s", status, reason or "")
        return "transient"


class FcmSender:
    def __init__(
        self,
        *,
        project_id: str,
        client_email: str,
        private_key: str,
        post: Callable | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if not (project_id and client_email and private_key):
            raise ValueError("FCM needs a project id, client email, and private key")
        self._project = project_id
        self._email = client_email
        self._key = private_key
        self._clock = clock
        self._access = None
        self._access_until = 0.0
        if post is None:
            import requests

            post = requests.post
        self._post = post

    @classmethod
    def from_service_account(cls, path: str, **kwargs) -> "FcmSender":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            project_id=data["project_id"],
            client_email=data["client_email"],
            private_key=data["private_key"],
            **kwargs,
        )

    def _access_token(self) -> str | None:
        now = self._clock()
        if self._access is not None and now < self._access_until - 60:
            return self._access
        assertion = jwt.encode(
            {
                "iss": self._email,
                "scope": FCM_SCOPE,
                "aud": GOOGLE_TOKEN_URL,
                "iat": int(now),
                "exp": int(now) + 3600,
            },
            self._key,
            algorithm="RS256",
        )
        response = self._post(
            GOOGLE_TOKEN_URL,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            },
            timeout=10,
        )
        if getattr(response, "status_code", None) != 200:
            return None
        token = _json_field(response, "access_token")
        if not isinstance(token, str):
            return None
        self._access = token
        lifetime = _json_field(response, "expires_in")
        self._access_until = now + (lifetime if isinstance(lifetime, int) else 3600)
        return token

    def send(self, *, token, locale, case_id, **_ignored) -> str:
        try:
            access = self._access_token()
            if access is None:
                log.warning("fcm access token refused")
                return "transient"
            response = self._post(
                f"https://fcm.googleapis.com/v1/projects/{self._project}/messages:send",
                headers={"Authorization": f"Bearer {access}"},
                json=fcm_message(token, case_id, locale),
                timeout=10,
            )
        except Exception as exc:
            log.warning("fcm send failed: %s", type(exc).__name__)
            return "transient"
        status = getattr(response, "status_code", None)
        if status == 200:
            return "sent"
        code = _fcm_error(response)
        if status == 404 or code in _FCM_PERMANENT:
            return "permanent"
        log.warning("fcm status %s %s", status, code or "")
        return "transient"


class PushRouter:
    """Sends to APNs or FCM by the member's `push_provider`."""

    def __init__(self, *, apns=None, fcm=None) -> None:
        self._senders = {"apns": apns, "fcm": fcm}

    def send(self, *, provider, token, env, locale, case_id) -> str:
        sender = self._senders.get(provider)
        if sender is None:
            log.warning("no push sender for %s", provider)
            return "transient"
        return sender.send(
            provider=provider, token=token, env=env, locale=locale, case_id=case_id
        )


def push_from_env(get: Callable[[str], str]) -> PushRouter | None:
    """APNs from APNS_*, FCM from FCM_SERVICE_ACCOUNT_FILE. None when neither is set."""
    apns = None
    if get("APNS_KEY_FILE"):
        apns = ApnsSender(
            team_id=get("APNS_TEAM_ID"),
            key_id=get("APNS_KEY_ID"),
            private_key=Path(get("APNS_KEY_FILE")).read_text(encoding="utf-8"),
            topic=get("APNS_TOPIC"),
        )
    fcm = None
    if get("FCM_SERVICE_ACCOUNT_FILE"):
        fcm = FcmSender.from_service_account(get("FCM_SERVICE_ACCOUNT_FILE"))
    if apns is None and fcm is None:
        return None
    return PushRouter(apns=apns, fcm=fcm)


def _json_field(response, name):
    try:
        data = response.json()
    except Exception:
        return None
    return data.get(name) if isinstance(data, dict) else None


def _fcm_error(response) -> str | None:
    try:
        error = response.json().get("error", {})
    except Exception:
        return None
    for detail in error.get("details", []) or []:
        code = detail.get("errorCode") if isinstance(detail, dict) else None
        if code:
            return code
    return error.get("status")
