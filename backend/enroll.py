"""Invite secrets, SMS OTP codes, and the SMS senders. Milestone 5.

Invite secret: 12 characters from a 31-character alphabet with no 0/O,
1/I/L, so it can be read over the phone. About 59 bits. It is shown to the
parent once, formatted `XXXX-XXXX-XXXX`, and stored only as
`keyed_hash("invite", secret)`. Lookup is by that hash, so it is an HMAC
keyed with CODE_PEPPER rather than a salted hash. Expiry (24 hours) and
single use are columns, checked by the store.

SMS OTP: 6 uniform digits, stored as `keyed_hash("phone_otp", phone:code)`,
so a challenge for one number does not match the same digits for another.
It proves the child controls the number. It is not the check code and it is
never asked for on the verification call. The message says so.

`DevOtp` records codes for tests and logs them. It exists only when
DEV_AUTH=1. `TwilioOtp` posts one message through the Twilio REST API.
Neither logs a full phone number.

Voice channel: when a Korean carrier blocks the SMS, the same challenge
can be read out by a Twilio call instead (`channel="voice"`). The TwiML
is sent inline with the call request (`Twiml`), so there is no webhook,
no URL that holds the digits, and nothing that touches a case. It is
`<Say>` only: no `<Gather>`, no `<Play>`, no recording. It proves the
number, like the SMS. It is not the verification call, and those digits
are not the one-time code a verification call asks for.
"""

import logging
import re
import secrets
from collections.abc import Callable, Mapping
from datetime import timedelta

import requests

from backend.codes import keyed_hash, keyed_hash_matches


log = logging.getLogger(__name__)

INVITE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
INVITE_LEN = 12
INVITE_TTL = timedelta(hours=24)
OTP_TTL = timedelta(minutes=10)
OTP_MAX_ATTEMPTS = 5
OTP_SENDS_PER_DAY = 5
OTP_CHANNELS = ("sms", "voice")
_INVITE_DOMAIN = "invite"
_OTP_DOMAIN = "phone_otp"
_SIX_DIGITS = re.compile(r"[0-9]{6}")
_INVITE_SEPARATORS = re.compile(r"[\s\-]")
# Largest multiple of 31 below 256, and of 10**6 below 2**32: draws at or
# above these are discarded so every character and every code is uniform.
_BYTE_LIMIT = (256 // len(INVITE_ALPHABET)) * len(INVITE_ALPHABET)
_WORD_LIMIT = ((1 << 32) // 1_000_000) * 1_000_000


class OtpSendFailed(Exception):
    """The provider did not accept the message. The text is a status, never the code."""


def new_invite_secret(rng: Callable[[int], bytes] | None = None) -> str:
    draw = rng if rng is not None else secrets.token_bytes
    out = []
    for _ in range(64):
        chunk = draw(32)
        if type(chunk) is not bytes or len(chunk) != 32:
            raise ValueError("rng must return the requested bytes")
        for byte in chunk:
            if byte < _BYTE_LIMIT:
                out.append(INVITE_ALPHABET[byte % len(INVITE_ALPHABET)])
                if len(out) == INVITE_LEN:
                    return "".join(out)
    raise RuntimeError("invite rng rejected too many bytes")


def format_invite(secret: str) -> str:
    return "-".join(secret[i : i + 4] for i in range(0, len(secret), 4))


def normalize_invite(raw: object) -> str | None:
    """Uppercase, without spaces or dashes. None when it cannot be an invite."""
    if not isinstance(raw, str) or len(raw) > 64:
        return None
    folded = _INVITE_SEPARATORS.sub("", raw).upper()
    if len(folded) != INVITE_LEN or any(ch not in INVITE_ALPHABET for ch in folded):
        return None
    return folded


def hash_invite(secret: str) -> str:
    return keyed_hash(_INVITE_DOMAIN, secret)


def new_otp_code(rng: Callable[[int], bytes] | None = None) -> str:
    draw = rng if rng is not None else secrets.token_bytes
    for _ in range(64):
        chunk = draw(4)
        if type(chunk) is not bytes or len(chunk) != 4:
            raise ValueError("rng must return the requested bytes")
        value = int.from_bytes(chunk, "big")
        if value < _WORD_LIMIT:
            return f"{value % 1_000_000:06d}"
    raise RuntimeError("otp rng rejected too many draws")


def hash_otp(phone_e164: str, code: str) -> str:
    if not isinstance(code, str) or _SIX_DIGITS.fullmatch(code) is None:
        raise ValueError("otp must be 6 digits")
    return keyed_hash(_OTP_DOMAIN, f"{phone_e164}:{code}")


def otp_matches(phone_e164: str, code: object, stored: object) -> bool:
    if not isinstance(code, str) or _SIX_DIGITS.fullmatch(code) is None:
        keyed_hash(_OTP_DOMAIN, f"{phone_e164}:000000")
        return False
    return keyed_hash_matches(_OTP_DOMAIN, f"{phone_e164}:{code}", stored)


def sms_language(phone_e164: str) -> str:
    """Same rule as the call: +82 is Korean, everything else English."""
    return "ko" if phone_e164.startswith("+82") else "en"


def otp_message(phone_e164: str, code: str) -> str:
    if sms_language(phone_e164) == "ko":
        return (
            f"[패밀리 쉴드] 전화번호 인증번호: {code}. "
            "다른 사람에게 알려주지 마세요. 확인 번호(체크 코드)가 아닙니다."
        )
    return (
        f"Family Shield phone verification code: {code}. "
        "Don't share it with anyone. This is not your check code."
    )


def otp_voice_twiml(phone_e164: str, code: str) -> str:
    """`<Say>` the six digits twice, in the number's language. Nothing else."""
    if not isinstance(code, str) or _SIX_DIGITS.fullmatch(code) is None:
        raise ValueError("otp must be 6 digits")
    spoken = ", ".join(code)
    if sms_language(phone_e164) == "ko":
        voice, language = "Polly.Seoyeon", "ko-KR"
        first = f"패밀리 쉴드 전화번호 인증번호입니다. {spoken}."
        again = f"다시 한 번 말씀드립니다. {spoken}. 확인 번호가 아닙니다."
    else:
        voice, language = "Polly.Joanna", "en-US"
        first = f"Your Family Shield phone verification code is {spoken}."
        again = f"Again, {spoken}. This is not your check code."
    say = f'<Say voice="{voice}" language="{language}">'
    return (
        '<?xml version="1.0" encoding="UTF-8"?><Response>'
        f"{say}{first}</Say><Pause length=\"1\"/>{say}{again}</Say>"
        "</Response>"
    )


class DevOtp:
    """Records `(phone, code)` and logs the code. DEV_AUTH=1 only."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []
        self.channels: list[str] = []

    def send(self, phone_e164: str, code: str, channel: str = "sms") -> None:
        if channel not in OTP_CHANNELS:
            raise ValueError("unknown otp channel")
        self.sent.append((phone_e164, code))
        self.channels.append(channel)
        log.info("dev otp (%s) for number ending %s: %s", channel, phone_e164[-4:], code)


class TwilioOtp:
    """One SMS through Twilio's Messages API. Not used when DEV_AUTH=1."""

    def __init__(
        self,
        *,
        account_sid: str,
        auth_token: str,
        from_number: str = "",
        messaging_service_sid: str = "",
        post: Callable = requests.post,
    ) -> None:
        if not account_sid or not auth_token:
            raise ValueError("account_sid and auth_token are required")
        if not from_number and not messaging_service_sid:
            raise ValueError("from_number or messaging_service_sid is required")
        self._sid = account_sid
        self._token = auth_token
        self._from = from_number
        self._service = messaging_service_sid
        self._post = post

    @classmethod
    def from_env(cls, env: Mapping[str, str], post: Callable = requests.post) -> "TwilioOtp":
        def get(name: str) -> str:
            value = env.get(name)
            return "" if value is None else str(value).strip()

        for name in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"):
            if get(name) == "":
                raise RuntimeError(f"{name} is required")
        if get("TWILIO_FROM_NUMBER") == "" and get("TWILIO_MESSAGING_SERVICE_SID") == "":
            raise RuntimeError(
                "TWILIO_FROM_NUMBER or TWILIO_MESSAGING_SERVICE_SID is required"
            )
        return cls(
            account_sid=get("TWILIO_ACCOUNT_SID"),
            auth_token=get("TWILIO_AUTH_TOKEN"),
            from_number=get("TWILIO_FROM_NUMBER"),
            messaging_service_sid=get("TWILIO_MESSAGING_SERVICE_SID"),
            post=post,
        )

    def send(self, phone_e164: str, code: str, channel: str = "sms") -> None:
        if channel == "voice":
            self._call(phone_e164, code)
            return
        if channel != "sms":
            raise ValueError("unknown otp channel")
        data = {"To": phone_e164, "Body": otp_message(phone_e164, code)}
        if self._service:
            data["MessagingServiceSid"] = self._service
        else:
            data["From"] = self._from
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self._sid}/Messages.json"
        response = self._post(url, data=data, auth=(self._sid, self._token), timeout=10)
        status = getattr(response, "status_code", None)
        if not isinstance(status, int) or not 200 <= status < 300:
            raise OtpSendFailed(f"twilio status {status}")

    def _call(self, phone_e164: str, code: str) -> None:
        if not self._from:
            # A messaging service can text but cannot place a call.
            raise OtpSendFailed("no voice number")
        data = {
            "To": phone_e164,
            "From": self._from,
            "Twiml": otp_voice_twiml(phone_e164, code),
            "Timeout": "30",
            "Record": "false",
        }
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self._sid}/Calls.json"
        response = self._post(url, data=data, auth=(self._sid, self._token), timeout=10)
        status = getattr(response, "status_code", None)
        if not isinstance(status, int) or not 200 <= status < 300:
            raise OtpSendFailed(f"twilio status {status}")
