"""The Twilio keypad fallback call. Milestone 6.

Pure helpers plus one REST client. No database access here: the API locks
the case, asks the store for the outcome, and asks this module for the TwiML.

- `call_language(e164)`: `ko` for +82, `en` for +1, ValueError otherwise.
  The device locale and the transcript language do not change it.
- Prompts are twelve mp3 files, `backend/prompts/{en,ko}/{name}.mp3`, made
  ahead of time by `scripts/render_prompts.py` (Cartesia `make_voice_message`).
  The live call never calls Cartesia and never `<Say>`s anything.
- Every `<Gather>` is `input="dtmf"`. The one-time gather is 6 digits and
  finishes on `*`. The static gather is 4 digits with no finish key. The
  answer gather is 1 digit. Every gather posts even when empty
  (`actionOnEmptyResult`), so star and silence on the one-time gather both
  arrive as `Digits=""`, which is the static switch, never a guess. Each
  document ends in `<Hangup/>` so nothing falls through to a default.
- `twilio_signature` is Twilio's documented scheme: HMAC-SHA1 of the full
  URL followed by the sorted POST parameters, keyed with the auth token,
  base64. The `case_id` query string is part of the signed URL.
- `TwilioCalls.place` creates one call with recording off and a 30-second
  ring. It returns the CallSid. Nothing here logs digits or a full number.
"""

import base64
import hashlib
import hmac
from collections.abc import Callable, Mapping
from pathlib import Path
from urllib.parse import urlencode
from xml.sax.saxutils import quoteattr

import requests


PROMPTS_DIR = Path(__file__).with_name("prompts")
LANGUAGES = ("en", "ko")
GATHER_TIMEOUT_SECONDS = 15
RING_TIMEOUT_SECONDS = 30

# The six lines from docs/PRODUCT_REDESIGN.md, "What the child is asked".
# scripts/render_prompts.py renders exactly these. The greeting carries the
# AI disclosure. No line includes an amount, a name, or the story.
PROMPT_LINES = {
    "en": {
        "one_time_greeting": (
            "Hi, this is Family Shield, an AI assistant calling for your family. "
            "They got a message that says it's from you. Open the Family Shield app, "
            "confirm it's you, and enter the six-digit code on your keypad. "
            "If you can't open the app, press star."
        ),
        "static_greeting": (
            "Hi, this is Family Shield, an AI assistant calling for your family. "
            "They just got a message that says it's from you, and they want to make "
            "sure you're okay. Please enter your four-digit check code on your "
            "phone's keypad now."
        ),
        "static_switch": "Enter your four-digit check code.",
        "code_failed": "We couldn't verify that. Goodbye.",
        "question": (
            "Thank you. Did you send your family a message asking for money? "
            "Press 1 for yes, or 2 for no."
        ),
        "thanks": "Thanks, I'll let your family know.",
    },
    "ko": {
        "one_time_greeting": (
            "안녕하세요. 패밀리 쉴드입니다. 가족을 대신해 전화하는 인공지능입니다. "
            "앱을 열고 본인 확인을 한 다음, 화면에 나온 여섯 자리 번호를 키패드로 "
            "입력해 주세요. 앱을 열 수 없으면 별표를 누르세요."
        ),
        "static_greeting": (
            "안녕하세요. 패밀리 쉴드입니다. 가족을 대신해 전화하는 인공지능입니다. "
            "가족에게 회원님인 척한 메시지가 와서, 맞는지 확인하려고 전화했습니다. "
            "키패드로 네 자리 확인 번호를 입력해 주세요."
        ),
        "static_switch": "네 자리 확인 번호를 입력해 주세요.",
        "code_failed": "확인하지 못했습니다. 전화를 종료합니다.",
        "question": (
            "감사합니다. 가족에게 돈을 부탁하는 메시지를 보낸 적이 있나요? "
            "맞으면 1, 아니면 2를 누르세요."
        ),
        "thanks": "감사합니다. 가족에게 전달하겠습니다.",
    },
}
PROMPT_NAMES = tuple(PROMPT_LINES["en"])


class CallPlaceFailed(Exception):
    """Twilio did not accept the call. The text is a status, never a number."""


def call_language(phone_e164: str) -> str:
    if not isinstance(phone_e164, str):
        raise ValueError("unsupported_country")
    if phone_e164.startswith("+82"):
        return "ko"
    if phone_e164.startswith("+1"):
        return "en"
    raise ValueError("unsupported_country")


def prompt_path(language: str, name: str, root: Path | None = None) -> Path:
    if language not in LANGUAGES or name not in PROMPT_NAMES:
        raise ValueError("unknown prompt")
    return (PROMPTS_DIR if root is None else root) / language / f"{name}.mp3"


def missing_prompts(root: Path | None = None) -> list[str]:
    """`lang/name.mp3` for every prompt file that is not on disk or is empty."""
    missing = []
    for language in LANGUAGES:
        for name in PROMPT_NAMES:
            path = prompt_path(language, name, root)
            if not path.is_file() or path.stat().st_size == 0:
                missing.append(f"{language}/{name}.mp3")
    return missing


class Voice:
    """URLs for one deployment. `base_url` is what Twilio sees, without a trailing slash."""

    def __init__(self, base_url: str) -> None:
        base = (base_url or "").strip().rstrip("/")
        if not base.startswith("https://") and not base.startswith("http://"):
            raise ValueError("PUBLIC_BASE_URL must be an http(s) URL")
        self.base_url = base

    def prompt_url(self, language: str, name: str) -> str:
        prompt_path(language, name)
        return f"{self.base_url}/voice/prompts/{language}/{name}.mp3"

    def hook(self, name: str, case_id) -> str:
        return f"{self.base_url}/voice/twilio/{name}?{urlencode({'case_id': str(case_id)})}"

    def code_gather(self, case_id, language: str, channel: str, prompt: str) -> str:
        """The one-time (6, `*` finishes) or static (4, no finish key) gather."""
        if channel == "one_time":
            digits, finish = 6, "*"
        elif channel == "static":
            digits, finish = 4, ""
        else:
            raise ValueError("unknown code channel")
        return _gather(
            self.hook("code", case_id), digits, finish, self.prompt_url(language, prompt)
        )

    def question(self, case_id, language: str) -> str:
        return _gather(
            self.hook("answer", case_id), 1, "", self.prompt_url(language, "question")
        )

    def play_and_hang_up(self, language: str, name: str) -> str:
        return _document(f"<Play>{_text(self.prompt_url(language, name))}</Play><Hangup/>")


def hang_up() -> str:
    return _document("<Hangup/>")


def _gather(action: str, num_digits: int, finish_on_key: str, play_url: str) -> str:
    attrs = (
        f'input="dtmf" numDigits="{num_digits}" finishOnKey={quoteattr(finish_on_key)} '
        f'timeout="{GATHER_TIMEOUT_SECONDS}" actionOnEmptyResult="true" '
        f"action={quoteattr(action)} method=\"POST\""
    )
    return _document(f"<Gather {attrs}><Play>{_text(play_url)}</Play></Gather><Hangup/>")


def _document(body: str) -> str:
    return f'<?xml version="1.0" encoding="UTF-8"?><Response>{body}</Response>'


def _text(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def twilio_signature(auth_token: str, url: str, params: Mapping[str, str]) -> str:
    payload = url + "".join(f"{key}{params[key]}" for key in sorted(params))
    digest = hmac.new(auth_token.encode("utf-8"), payload.encode("utf-8"), hashlib.sha1)
    return base64.b64encode(digest.digest()).decode("ascii")


def valid_signature(auth_token: str, url: str, params: Mapping[str, str], header) -> bool:
    if not auth_token or not isinstance(header, str) or header == "":
        return False
    expected = twilio_signature(auth_token, url, params)
    return hmac.compare_digest(expected.encode("ascii"), header.encode("ascii", "replace"))


class TwilioCalls:
    """Creates the fallback call through Twilio's REST API."""

    def __init__(
        self,
        *,
        account_sid: str,
        auth_token: str,
        from_number: str,
        voice: Voice,
        post: Callable = requests.post,
    ) -> None:
        if not account_sid or not auth_token or not from_number:
            raise ValueError("account_sid, auth_token, and from_number are required")
        self._sid = account_sid
        self._token = auth_token
        self._from = from_number
        self._voice = voice
        self._post = post

    def place(self, phone_e164: str, *, case_id) -> str:
        call_language(phone_e164)
        data = {
            "To": phone_e164,
            "From": self._from,
            "Url": self._voice.hook("outbound", case_id),
            "Method": "POST",
            "StatusCallback": self._voice.hook("status", case_id),
            "StatusCallbackMethod": "POST",
            "Timeout": str(RING_TIMEOUT_SECONDS),
            "Record": "false",
        }
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self._sid}/Calls.json"
        response = self._post(url, data=data, auth=(self._sid, self._token), timeout=10)
        status = getattr(response, "status_code", None)
        if not isinstance(status, int) or not 200 <= status < 300:
            raise CallPlaceFailed(f"twilio status {status}")
        try:
            sid = response.json().get("sid")
        except Exception:
            sid = None
        if not isinstance(sid, str) or not sid.startswith("CA"):
            raise CallPlaceFailed("twilio returned no call sid")
        return sid
