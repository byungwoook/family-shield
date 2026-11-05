"""Product HTTP API. Milestone 4: the loop pytest can run without a handset.

The hackathon app from `services.code_webhook.make_app` is a different
process. This module does not mount it and does not call `_yes_no`.
Keypad text is folded with `_digits`. `apply_keypad` is the decision the
Twilio routes wrap later. Those routes are not registered here.

`clock` returns an aware datetime. `rng(n) -> bytes` is the salt and nonce
source. `tokens() -> str` mints a session secret. Handlers commit. The
store does not. A call is recorded only after that commit, as the string
"would call {e164}". Nothing is dialed.

`boot` refuses to start when `ENV=production` and `DEV_AUTH=1`. The dev
login and the helpers that skip SMS exist only in that mode.

Milestone 5 adds Apple and Google sign-in (`backend.signin`), invite
secrets, SMS OTP for +1 and +82 (`backend.enroll`), and the parent's
confirm or reject. Outside DEV_AUTH=1, boot requires both sign-in
audiences and a Twilio sender, so `DevOtp` cannot be the production path.
The SMS, like the call, is sent only after the commit.

Milestone 6 adds the Twilio keypad call (`backend.calls`): the call is
placed after the commit, and its CallSid or its failure is written in a
second transaction. `/voice/twilio/*` checks `X-Twilio-Signature` against
PUBLIC_BASE_URL plus the path and query, and the CallSid against the
attempt stored for that case. A webhook that fails either check changes
nothing. Digits are never logged. `GET /v1/cases/{id}/call-code` shows
the one-time code to the child's session only.

`GET /v1/cases/{id}` is an allowlist. It has no code, no nonce, no hash,
and no full phone number. `phone_last4` is the only phone fragment. The
child's session gets a smaller allowlist (`child_case`): the state and the
outcome of the fixed `money_request` question, and nothing that came from
the suspicious message.
"""

import hashlib
import logging
import os
import re
import secrets
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl
from uuid import UUID, uuid4

from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from backend.calls import (
    PROMPTS_DIR,
    TwilioCalls,
    Voice,
    call_language,
    hang_up,
    missing_prompts,
    prompt_path,
    valid_signature,
)

from backend.codes import (
    BiometricRequired,
    CodeConfigError,
    DerivationKeyError,
)
from backend.enroll import (
    INVITE_TTL,
    OTP_MAX_ATTEMPTS,
    OTP_SENDS_PER_DAY,
    OTP_TTL,
    DevOtp,
    TwilioOtp,
    format_invite,
    hash_invite,
    hash_otp,
    new_invite_secret,
    new_otp_code,
    normalize_invite,
    otp_matches,
)
from backend.signin import InvalidIdToken, apple_verifier, google_verifier
from backend.store import (
    CaseNotFound,
    PhoneInUse,
    RateLimited,
    accept_invite,
    active_parent,
    call_attempt,
    call_code,
    add_family_event,
    add_member,
    apply_case,
    check_phone_otp,
    child_membership,
    complete_phone_otp,
    confirm_member,
    create_family,
    create_session,
    end_call_attempt,
    ensure_user,
    family_roster,
    finish_call_attempt,
    issue_invite,
    load_case,
    lock_case,
    mark_member_callable,
    member_contact,
    memberships_for_user,
    open_case,
    record_call_attempt,
    reject_member,
    session_user,
    set_check_code,
    start_phone_otp,
    submit_digits,
)
from services.code_webhook import _digits


log = logging.getLogger(__name__)

SESSION_TTL = timedelta(days=30)
_NAME_LIMIT = 200
_TEXT_LIMIT = 8000
_DIGITS_LIMIT = 32
_TOKEN_LIMIT = 512
_TERMINAL = frozenset({"confirmed", "scam", "not_confirmed"})
_E164 = re.compile(r"^\+[1-9][0-9]{1,14}$")
_SUBJECT = re.compile(r"[A-Za-z0-9._:-]{1,200}")
_DEV_PROVIDER = "apple"

# Stable ValueError text raised by the store and by codes.py. The response
# uses the mapped code and never the exception text, which can name a column
# but must not be a place a code could land later.
_VALUE_ERRORS = {
    "not_a_child": (400, "not_a_child"),
    "member_removed": (400, "member_not_callable"),
    "phone_already_set": (409, "phone_already_set"),
    "user_not_found": (404, "not_found"),
    "user_already_in_a_family": (409, "already_in_a_family"),
    "child_not_in_family": (400, "member_not_callable"),
    "invalid_phone": (400, "invalid_phone"),
    "check code is child only": (403, "not_a_child"),
    "static check code must be 4 digits": (400, "invalid_code"),
    "token_hash_too_short": (500, "config"),
    "invite_invalid": (400, "invite_invalid"),
    "invite_expired": (400, "invite_expired"),
    "invite_not_open": (409, "invite_not_open"),
    "member_not_ready": (409, "member_not_ready"),
    "member_not_pending": (409, "member_not_pending"),
}


class APIError(Exception):
    """A finished HTTP error. The body is `{"error": code}` and nothing else."""

    def __init__(self, status: int, code: str):
        super().__init__(code)
        self.status = status
        self.code = code


class UnsupportedCountry(Exception):
    """A well-formed E.164 number whose country is not +1 or +82."""


class InvalidPhone(Exception):
    """A value that is not E.164."""


class FamilyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(max_length=_NAME_LIMIT)


class ChildIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str = Field(max_length=_NAME_LIMIT)


class ActivateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phone_e164: str = Field(max_length=16)
    user_id: UUID | None = None


class CheckCodeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(max_length=16)
    biometric_ok: bool


class CaseIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    child_member_id: UUID
    text: str = Field(default="", max_length=_TEXT_LIMIT)


class AnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str = Field(max_length=8)


class DigitsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    digits: str = Field(max_length=_DIGITS_LIMIT)


class SignInIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id_token: str = Field(max_length=8192)
    locale: str
    display_name: str | None = Field(default=None, max_length=_NAME_LIMIT)


class InviteAcceptIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    secret: str = Field(max_length=64)


class OtpStartIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phone_e164: str = Field(max_length=16)


class OtpCheckIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phone_e164: str = Field(max_length=16)
    code: str = Field(max_length=16)


class DecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(max_length=16)


class DevLoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str = Field(max_length=_NAME_LIMIT)
    locale: str
    auth_subject: str | None = None


class RecordingCallProvider:
    """Records `would call {e164}`. Does not open a socket.

    Returns no CallSid, so no Twilio webhook can ever match its attempt.
    """

    def __init__(self) -> None:
        self.calls: list[str] = []

    def place(self, phone_e164: str, *, case_id=None) -> None:
        if not isinstance(phone_e164, str) or phone_e164 == "":
            raise ValueError("phone_e164 is required")
        self.calls.append(f"would call {phone_e164}")
        return None


def default_clock() -> datetime:
    return datetime.now(timezone.utc)


def default_rng(n: int) -> bytes:
    return secrets.token_bytes(n)


def default_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 hex of a session token. The token is high entropy, not a PIN."""
    if not isinstance(token, str):
        raise TypeError("token must be a str")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def phone_region(e164: str) -> str:
    """`us` for +1, `kr` for +82. Anything else is refused before a write.

    +1 is the whole NANP prefix. +82 is checked first so it is not read as +1.
    """
    if not isinstance(e164, str) or _E164.fullmatch(e164) is None:
        raise InvalidPhone("invalid_phone")
    if e164.startswith("+82"):
        return "kr"
    if e164.startswith("+1"):
        return "us"
    raise UnsupportedCountry("unsupported_country")


def child_callable(member: dict) -> bool:
    """Active, parent-confirmed, and reachable by an opted-in phone or a push token."""
    if member.get("role") != "child" or member.get("status") != "active":
        return False
    if member.get("confirmed_by_parent_at") is None:
        return False
    phone = member.get("phone_e164")
    opted_in = (
        isinstance(phone, str)
        and phone != ""
        and member.get("phone_opted_in_at") is not None
    )
    token = member.get("push_token")
    has_push = isinstance(token, str) and token.strip() != ""
    return opted_in or has_push


def color_of(state: str) -> str:
    """Parent-facing color. The state remains the source of truth."""
    if state == "confirmed":
        return "green"
    if state == "scam":
        return "red"
    if state == "not_confirmed":
        return "yellow"
    return "open"


def gather_for(case: dict) -> str | None:
    """What the next keypad prompt would ask for. None means hang up."""
    if case.get("state") == "calling":
        return case.get("code_channel")
    if case.get("state") == "awaiting_answer":
        return "answer"
    return None


def public_case(view: dict, *, child_name: str, phone_last4: str | None) -> dict:
    """Allowlisted case body. Extra keys on `view`, including codes, are dropped."""
    return {
        "id": str(view["id"]),
        "family_id": str(view["family_id"]),
        "child_member_id": str(view["child_member_id"]),
        "child_display_name": child_name,
        "state": view["state"],
        "result": view["result"],
        "color": color_of(view["state"]),
        "answered_via": view["answered_via"],
        "code_channel": view["code_channel"],
        "parent_text": view["parent_text"],
        "transcript": view["transcript"],
        "claims": view["claims"],
        "pattern_id": view["pattern_id"],
        "timeline": list(view.get("events") or []),
        "phone_last4": phone_last4,
        "deadline_at": _iso(view["deadline_at"]),
        "created_at": _iso(view["created_at"]),
        "updated_at": _iso(view["updated_at"]),
        "decided_at": _iso(view["decided_at"]),
    }


CHILD_CASE_KEYS = (
    "id",
    "child_member_id",
    "kind",
    "state",
    "result",
    "color",
    "answered_via",
    "code_channel",
    "gather",
    "deadline_at",
    "created_at",
    "updated_at",
    "decided_at",
)


def child_case(body: dict) -> dict:
    """What the child's session sees: whether a question is open, and the outcome.

    The question is the fixed `money_request`. The parent's text, the
    transcript, the claims, the pattern, the timeline, and the number are
    left out: they come from the suspicious message, and the child answers
    the same fixed question on every case, in the app or on the call.
    """
    view = {key: body.get(key) for key in CHILD_CASE_KEYS if key != "kind"}
    view["kind"] = "money_request"
    return {key: view[key] for key in CHILD_CASE_KEYS}


def keypad_action(case: dict, raw: str) -> tuple[str, str]:
    """What one keypad submission means. Spoken words are not answers.

    Returns `(action, digits)`. `action` is `digits`, `answer_yes`,
    `answer_no`, `answer_unclear`, or `ignore`. Digits are `_digits(raw)`
    except for a bare `*`, which is preserved so the store can see star.

    A single digit while the case is still asking for a code is `ignore`.
    The 1/2 question is not a guess, and it must not end the call as a
    wrong code. `_yes_no` is not used: "yes" folds to an empty string.
    """
    if not isinstance(raw, str):
        raise TypeError("digits must be a str")
    state = case.get("state")
    if state == "awaiting_answer":
        folded = _digits(raw)
        if folded == "1":
            return "answer_yes", folded
        if folded == "2":
            return "answer_no", folded
        return "answer_unclear", folded
    if state == "calling":
        if raw.strip() == "*":
            return "digits", "*"
        folded = _digits(raw)
        if len(folded) == 1:
            return "ignore", folded
        return "digits", folded
    return "ignore", _digits(raw)


def apply_keypad(conn, case_id: UUID, raw: str, *, now: datetime, rng=None) -> dict:
    """Fold one keypad submission and apply it. Does not commit.

    The return value is the store view. Callers that speak HTTP have to
    pass it through `public_case`. A premature single digit writes nothing.
    """
    view = lock_case(conn, case_id, now=now)
    action, digits = keypad_action(view, raw)
    if action == "ignore":
        return view
    if action == "digits":
        return submit_digits(conn, case_id, digits, now=now)
    return apply_case(conn, case_id, action, now=now, rng=rng)


def boot(environ: Mapping[str, str] | None = None) -> FastAPI:
    """Build the app from the environment. Missing secrets refuse to boot.

    `DEV_AUTH` is on only when the value is exactly `1`. That flag cannot
    be combined with `ENV=production`. `CODE_WEBHOOK_SECRET` belongs to the
    hackathon webhook, not to this process.

    With DEV_AUTH=1, SMS goes to `DevOtp` and a blank sign-in audience
    leaves that route answering `sign_in_unavailable`. Without it,
    APPLE_BUNDLE_ID, GOOGLE_SERVER_CLIENT_ID, and the Twilio settings are
    required and a missing one refuses to boot.

    Calls: with TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER,
    and PUBLIC_BASE_URL all set, calls go to Twilio and the voice routes
    exist. With DEV_AUTH=1 and any of them blank, calls are only recorded.
    Without DEV_AUTH=1 all four are required, and so are the twelve prompt
    files under PROMPTS_DIR (default backend/prompts): a call that plays
    nothing must not reach a child.
    """
    env = os.environ if environ is None else environ

    def get(name: str) -> str:
        value = env.get(name)
        if value is None:
            return ""
        return str(value).strip()

    if get("ENV") == "production" and get("DEV_AUTH") == "1":
        raise RuntimeError("DEV_AUTH must not be set when ENV=production")
    database_url = get("DATABASE_URL")
    if database_url == "":
        raise RuntimeError("DATABASE_URL is required")
    if get("CODE_PEPPER") == "":
        raise RuntimeError("CODE_PEPPER is required")
    if get("OTP_DERIVATION_KEY") == "":
        raise RuntimeError("OTP_DERIVATION_KEY is required")
    dev_auth = get("DEV_AUTH") == "1"
    apple_audience = get("APPLE_BUNDLE_ID")
    google_audience = get("GOOGLE_SERVER_CLIENT_ID")
    if not dev_auth:
        for name, value in (
            ("APPLE_BUNDLE_ID", apple_audience),
            ("GOOGLE_SERVER_CLIENT_ID", google_audience),
        ):
            if value == "":
                raise RuntimeError(f"{name} is required")
    otp_sender = DevOtp() if dev_auth else TwilioOtp.from_env(env)
    prompts_dir = Path(get("PROMPTS_DIR")) if get("PROMPTS_DIR") else PROMPTS_DIR
    voice_settings = {
        name: get(name)
        for name in (
            "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN",
            "TWILIO_FROM_NUMBER",
            "PUBLIC_BASE_URL",
        )
    }
    if not dev_auth:
        for name, value in voice_settings.items():
            if value == "":
                raise RuntimeError(f"{name} is required")
        missing = missing_prompts(prompts_dir)
        if missing:
            raise RuntimeError(
                f"{len(missing)} voice prompt files are missing; "
                "run: python -m scripts.render_prompts"
            )
    voice = None
    twilio_token = ""
    call_provider = RecordingCallProvider()
    if all(voice_settings.values()):
        voice = Voice(voice_settings["PUBLIC_BASE_URL"])
        twilio_token = voice_settings["TWILIO_AUTH_TOKEN"]
        call_provider = TwilioCalls(
            account_sid=voice_settings["TWILIO_ACCOUNT_SID"],
            auth_token=twilio_token,
            from_number=voice_settings["TWILIO_FROM_NUMBER"],
            voice=voice,
        )
        if missing_prompts(prompts_dir):
            log.warning("voice prompt files are missing; calls will play nothing")
    verifiers = {
        "apple": apple_verifier(apple_audience) if apple_audience else None,
        "google": google_verifier(google_audience) if google_audience else None,
    }

    def connect():
        import psycopg

        return psycopg.connect(database_url)

    return create_app(
        connect=connect,
        clock=default_clock,
        rng=default_rng,
        tokens=default_token,
        call_provider=call_provider,
        dev_auth=dev_auth,
        verifiers=verifiers,
        otp_sender=otp_sender,
        voice=voice,
        twilio_auth_token=twilio_token,
        prompts_dir=prompts_dir,
    )


def create_app(
    *,
    connect: Callable,
    clock: Callable[[], datetime],
    rng: Callable[[int], bytes],
    tokens: Callable[[], str],
    call_provider,
    dev_auth: bool,
    verifiers: Mapping | None = None,
    otp_sender=None,
    invite_secrets: Callable[[], str] = new_invite_secret,
    otp_codes: Callable[[], str] = new_otp_code,
    voice: Voice | None = None,
    twilio_auth_token: str = "",
    prompts_dir: Path = PROMPTS_DIR,
) -> FastAPI:
    """Routes for one product process. Dependencies are injected.

    `verifiers` maps `apple` / `google` to an `IdTokenVerifier` or None.
    `otp_sender.send(phone, code)` runs after the commit. When it is None
    the OTP routes answer `otp_unavailable` and write nothing.
    `voice` and `twilio_auth_token` together turn on `/voice/*`. Without
    both, there are no voice routes and no webhook can move a case.
    """
    verifiers = dict(verifiers or {})
    app = FastAPI(title="Family Shield")
    # Read by tests to check which sender boot chose. Not used by a route.
    app.state.otp_sender = otp_sender
    app.state.call_provider = call_provider

    @app.exception_handler(RequestValidationError)
    async def _invalid_body(_request: Request, _exc: RequestValidationError):
        # The default 422 body echoes the payload, which may be a code.
        return JSONResponse({"error": "invalid_body"}, status_code=400)

    @contextmanager
    def _transaction():
        conn = connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _run(work):
        try:
            with _transaction() as conn:
                return work(conn)
        except APIError as exc:
            return _fail(exc.status, exc.code)
        except CaseNotFound:
            return _fail(404, "not_found")
        except PhoneInUse:
            return _fail(409, "phone_in_use")
        except RateLimited:
            return _fail(429, "rate_limited")
        except InvalidIdToken:
            return _fail(401, "invalid_token")
        except BiometricRequired:
            return _fail(403, "biometric_required")
        except UnsupportedCountry:
            return _fail(400, "unsupported_country")
        except InvalidPhone:
            return _fail(400, "invalid_phone")
        except (CodeConfigError, DerivationKeyError):
            log.error("code config missing")
            return _fail(500, "config")
        except ValueError as exc:
            status, code = _from_value(exc)
            return _fail(status, code)
        except Exception as exc:
            log.error("request failed: %s", type(exc).__name__)
            return _fail(500, "unavailable")

    def _now() -> datetime:
        now = clock()
        if (
            not isinstance(now, datetime)
            or now.tzinfo is None
            or now.tzinfo.utcoffset(now) is None
        ):
            raise APIError(500, "config")
        return now

    def _user(conn, authorization: str | None) -> dict:
        token = _bearer(authorization)
        if token is None:
            raise APIError(401, "unauthorized")
        found = session_user(conn, hash_token(token), now=_now())
        if found is None:
            raise APIError(401, "unauthorized")
        return found

    def _present(conn, view: dict, role: str = "parent") -> dict:
        member = member_contact(conn, view["child_member_id"])
        phone = None if member is None else member.get("phone_e164")
        last4 = phone[-4:] if isinstance(phone, str) and len(phone) >= 4 else None
        name = member["display_name"] if member else ""
        body = public_case(view, child_name=name, phone_last4=last4)
        body["gather"] = gather_for(view)
        if role == "child":
            return child_case(body)
        return body

    def _visible(conn, user_id, view) -> str:
        member = member_contact(conn, view["child_member_id"])
        if member is None:
            raise APIError(404, "not_found")
        if member.get("user_id") == user_id:
            return "child"
        if active_parent(conn, user_id, view["family_id"]) is not None:
            return "parent"
        raise APIError(404, "not_found")

    if dev_auth:

        @app.post("/v1/dev/login")
        def dev_login(body: DevLoginIn):
            result = _run(lambda conn: _dev_login(conn, body))
            return _created(result)

        @app.post("/v1/dev/members/{member_id}/activate")
        def activate_member(
            member_id: str,
            body: ActivateIn,
            authorization: str | None = Header(default=None),
        ):
            result = _run(lambda conn: _activate(conn, authorization, member_id, body))
            return _created(result)

        @app.post("/v1/dev/members/{member_id}/check-code")
        def dev_check_code(
            member_id: str,
            body: CheckCodeIn,
            authorization: str | None = Header(default=None),
        ):
            return _run(lambda conn: _dev_check_code(conn, authorization, member_id, body))

        @app.post("/v1/dev/cases/{case_id}/digits")
        def post_digits(
            case_id: str,
            body: DigitsIn,
            authorization: str | None = Header(default=None),
        ):
            return _run(lambda conn: _digits_route(conn, authorization, case_id, body))

    @app.post("/v1/families")
    def post_family(body: FamilyIn, authorization: str | None = Header(default=None)):
        result = _run(lambda conn: _create_family(conn, authorization, body))
        return _created(result)

    @app.post("/v1/families/{family_id}/children")
    def post_child(
        family_id: str,
        body: ChildIn,
        authorization: str | None = Header(default=None),
    ):
        result = _run(lambda conn: _add_child(conn, authorization, family_id, body))
        return _created(result)

    @app.post("/v1/me/check-code")
    def post_check_code(
        body: CheckCodeIn,
        authorization: str | None = Header(default=None),
    ):
        return _run(lambda conn: _my_check_code(conn, authorization, body))

    @app.post("/v1/cases")
    def post_case(body: CaseIn, authorization: str | None = Header(default=None)):
        result = _run(lambda conn: _open(conn, authorization, body))
        if isinstance(result, JSONResponse):
            return result
        payload, dial = result
        if dial is None:
            return JSONResponse(payload, status_code=201)
        phone, case_id, attempt_id = dial
        try:
            ref = call_provider.place(phone, case_id=case_id)
            failed = False
        except Exception as exc:
            log.error("call provider failed: %s", type(exc).__name__)
            ref, failed = None, True
        after = _run(lambda conn: _after_dial(conn, case_id, attempt_id, ref, failed))
        if isinstance(after, JSONResponse):
            # The case is committed and stays `calling`; its timers decide it.
            return JSONResponse(payload, status_code=201)
        return JSONResponse(after, status_code=201)

    @app.get("/v1/cases/{case_id}/call-code")
    def get_call_code(case_id: str, authorization: str | None = Header(default=None)):
        result = _run(lambda conn: _call_code(conn, authorization, case_id))
        if isinstance(result, JSONResponse):
            return result
        return JSONResponse(result, headers={"Cache-Control": "no-store"})

    if voice is not None and twilio_auth_token:

        @app.get("/voice/prompts/{language}/{name}.mp3")
        def get_prompt(language: str, name: str):
            try:
                path = prompt_path(language, name, prompts_dir)
            except ValueError:
                return Response(status_code=404)
            if not path.is_file():
                return Response(status_code=404)
            return FileResponse(path, media_type="audio/mpeg")

        @app.post("/voice/twilio/{kind}")
        async def twilio_hook(kind: str, request: Request):
            if kind not in ("outbound", "code", "answer", "status"):
                return Response(status_code=404)
            raw = (await request.body()).decode("utf-8", "replace")
            params = dict(parse_qsl(raw, keep_blank_values=True))
            query = request.url.query
            url = voice.base_url + request.url.path + (f"?{query}" if query else "")
            header = request.headers.get("X-Twilio-Signature")
            if not valid_signature(twilio_auth_token, url, params, header):
                return Response(status_code=403)
            case_id = request.query_params.get("case_id", "")
            try:
                xml = await run_in_threadpool(_voice_work, kind, case_id, params)
            except Exception as exc:
                # No verdict from a crash: hang up and let the timers decide.
                log.error("voice %s failed: %s", kind, type(exc).__name__)
                xml = hang_up()
            return Response(xml, media_type="application/xml")

    def _voice_work(kind: str, case_id: str, params: dict) -> str:
        try:
            case_uuid = UUID(case_id)
        except (TypeError, ValueError):
            return hang_up()
        conn = connect()
        try:
            xml = _voice_tx(conn, kind, case_uuid, params)
            conn.commit()
            return xml
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _voice_tx(conn, kind: str, case_id: UUID, params: dict) -> str:
        now = _now()
        try:
            view = lock_case(conn, case_id, now=now)
        except CaseNotFound:
            return hang_up()
        attempt = call_attempt(conn, case_id, params.get("CallSid", ""))
        if attempt is None:
            return hang_up()
        member = member_contact(conn, view["child_member_id"])
        try:
            language = call_language(None if member is None else member.get("phone_e164"))
        except ValueError:
            return hang_up()
        if kind == "status":
            return _call_status(conn, view, attempt, params.get("CallStatus", ""), now)
        if kind == "outbound":
            if view["state"] != "calling":
                return hang_up()
            return _code_gather(view, language, first=True)
        digits = params.get("Digits", "")
        if kind == "code":
            return _code_hook(conn, view, language, digits, now)
        return _answer_hook(conn, view, language, digits, now)

    def _code_gather(view: dict, language: str, *, first: bool) -> str:
        channel = view["code_channel"]
        if channel == "one_time":
            prompt = "one_time_greeting"
        elif first and not view.get("has_app"):
            prompt = "static_greeting"
        else:
            prompt = "static_switch"
        return voice.code_gather(view["id"], language, channel, prompt)

    def _code_hook(conn, view: dict, language: str, digits: str, now) -> str:
        if view["state"] == "awaiting_answer":
            return voice.question(view["id"], language)
        if view["state"] != "calling":
            return hang_up()
        action, folded = keypad_action(view, digits)
        if action == "ignore":
            return _code_gather(view, language, first=False)
        after = submit_digits(conn, view["id"], folded, now=now)
        if after["state"] == "awaiting_answer":
            return voice.question(view["id"], language)
        if after["state"] == "calling":
            if after["code_channel"] != view["code_channel"] or folded == "*":
                return voice.code_gather(view["id"], language, "static", "static_switch")
            # Silence on the static gather. No guess was made; the call ends
            # and the status callback or the code window decides the case.
            return hang_up()
        if after["result"] in ("wrong", "code_locked"):
            return voice.play_and_hang_up(language, "code_failed")
        return hang_up()

    def _answer_hook(conn, view: dict, language: str, digits: str, now) -> str:
        if view["state"] == "calling":
            return _code_gather(view, language, first=False)
        if view["state"] != "awaiting_answer":
            return hang_up()
        action, _folded = keypad_action(view, digits)
        if action not in ("answer_yes", "answer_no", "answer_unclear"):
            action = "answer_unclear"
        apply_case(conn, view["id"], action, now=now, rng=rng)
        return voice.play_and_hang_up(language, "thanks")

    def _call_status(conn, view: dict, attempt: dict, status: str, now) -> str:
        """Twilio's final status. Nobody answering is never a no."""
        ended = status in ("completed", "busy", "no-answer", "failed", "canceled")
        if not ended:
            return hang_up()
        failed = status != "completed"
        end_call_attempt(conn, attempt["id"], failed=failed, now=now)
        state = view["state"]
        event = step = None
        if status in ("busy", "no-answer") and state == "calling":
            event, step = "code_window_elapsed", f"call_{status.replace('-', '_')}"
        elif status in ("failed", "canceled") and state == "calling":
            event, step = "call_failed", "call_failed"
        elif status == "completed" and state == "calling":
            event, step = "code_window_elapsed", "call_ended_before_code"
        elif state == "awaiting_answer":
            event, step = "answer_window_elapsed", "call_ended_before_answer"
        if event is not None:
            apply_case(conn, view["id"], event, now=now, rng=rng, step=step)
        return hang_up()

    @app.get("/v1/cases/{case_id}")
    def get_case(case_id: str, authorization: str | None = Header(default=None)):
        return _run(lambda conn: _get_case(conn, authorization, case_id))

    @app.post("/v1/cases/{case_id}/answer")
    def post_answer(
        case_id: str,
        body: AnswerIn,
        authorization: str | None = Header(default=None),
    ):
        return _run(lambda conn: _answer(conn, authorization, case_id, body))

    @app.post("/v1/auth/apple")
    def auth_apple(body: SignInIn):
        if verifiers.get("apple") is None:
            return _fail(503, "sign_in_unavailable")
        return _run(lambda conn: _sign_in(conn, "apple", body))

    @app.post("/v1/auth/google")
    def auth_google(body: SignInIn):
        if verifiers.get("google") is None:
            return _fail(503, "sign_in_unavailable")
        return _run(lambda conn: _sign_in(conn, "google", body))

    @app.get("/v1/families/{family_id}/members")
    def get_members(family_id: str, authorization: str | None = Header(default=None)):
        return _run(lambda conn: _roster(conn, authorization, family_id))

    @app.post("/v1/families/{family_id}/members/{member_id}/invite")
    def post_invite(
        family_id: str,
        member_id: str,
        authorization: str | None = Header(default=None),
    ):
        result = _run(lambda conn: _reissue(conn, authorization, family_id, member_id))
        return _created(result)

    @app.post("/v1/families/{family_id}/members/{member_id}/confirm")
    def post_confirm(
        family_id: str,
        member_id: str,
        body: DecisionIn,
        authorization: str | None = Header(default=None),
    ):
        return _run(
            lambda conn: _decide(conn, authorization, family_id, member_id, body)
        )

    @app.post("/v1/invites/accept")
    def post_accept(body: InviteAcceptIn, authorization: str | None = Header(default=None)):
        return _run(lambda conn: _accept(conn, authorization, body))

    @app.post("/v1/phones/otp")
    def post_otp(body: OtpStartIn, authorization: str | None = Header(default=None)):
        if otp_sender is None:
            return _fail(503, "otp_unavailable")
        result = _run(lambda conn: _otp_start(conn, authorization, body))
        if isinstance(result, JSONResponse):
            return result
        payload, phone, code = result
        try:
            otp_sender.send(phone, code)
        except Exception as exc:
            log.error("otp sender failed: %s", type(exc).__name__)
            return _fail(502, "sms_failed")
        return JSONResponse(payload, status_code=202)

    @app.post("/v1/phones/otp/check")
    def post_otp_check(body: OtpCheckIn, authorization: str | None = Header(default=None)):
        if otp_sender is None:
            return _fail(503, "otp_unavailable")
        return _run(lambda conn: _otp_check(conn, authorization, body))

    def _new_session(conn, user_id, now) -> str:
        token = tokens()
        if not isinstance(token, str) or len(token) < 32 or token.strip() != token:
            raise APIError(500, "config")
        digest = hash_token(token)
        if digest == token:
            raise APIError(500, "config")
        create_session(
            conn,
            user_id=user_id,
            token_hash=digest,
            expires_at=now + SESSION_TTL,
        )
        return token

    def _sign_in(conn, provider: str, body: SignInIn) -> dict:
        verifier = verifiers.get(provider)
        if verifier is None:
            raise APIError(503, "sign_in_unavailable")
        if body.locale not in ("en", "ko"):
            raise APIError(400, "invalid_body")
        now = _now()
        identity = verifier.verify(body.id_token, now=now)
        name = "" if body.display_name is None else body.display_name.strip()
        user_id = ensure_user(
            conn,
            auth_provider=identity.provider,
            auth_subject=identity.subject,
            display_name=name,
            locale=body.locale,
            now=now,
        )
        token = _new_session(conn, user_id, now)
        return {"token": token, "user_id": str(user_id)}

    def _new_invite(conn, member_id, family_id, actor, now, step) -> dict:
        secret = invite_secrets()
        if normalize_invite(secret) != secret:
            raise APIError(500, "config")
        expires_at = now + INVITE_TTL
        issue_invite(
            conn, member_id, invite_hash=hash_invite(secret), expires_at=expires_at
        )
        add_family_event(conn, family_id, now=now, actor_user_id=actor, step=step)
        return {
            "invite_secret": format_invite(secret),
            "invite_expires_at": _iso(expires_at),
        }

    def _family_child(conn, user_id, family_id: str, member_id: str) -> dict:
        family = _uuid(family_id)
        if active_parent(conn, user_id, family) is None:
            raise APIError(404, "not_found")
        member = member_contact(conn, _uuid(member_id))
        if (
            member is None
            or member["family_id"] != family
            or member.get("role") != "child"
            or member.get("status") == "removed"
        ):
            raise APIError(404, "not_found")
        return member

    def _roster(conn, authorization, family_id: str) -> dict:
        user = _user(conn, authorization)
        family = _uuid(family_id)
        if active_parent(conn, user["user_id"], family) is None:
            raise APIError(404, "not_found")
        members = []
        for row in family_roster(conn, family):
            members.append(
                {
                    **row,
                    "id": str(row["id"]),
                    "invite_expires_at": _iso(row["invite_expires_at"]),
                    "confirmed_at": _iso(row["confirmed_at"]),
                }
            )
        return {"family_id": str(family), "members": members}

    def _reissue(conn, authorization, family_id: str, member_id: str) -> dict:
        now = _now()
        user = _user(conn, authorization)
        member = _family_child(conn, user["user_id"], family_id, member_id)
        invite = _new_invite(
            conn, member["id"], member["family_id"], user["user_id"], now, "invite_reissued"
        )
        return {"id": str(member["id"]), **invite}

    def _decide(conn, authorization, family_id: str, member_id: str, body: DecisionIn):
        now = _now()
        user = _user(conn, authorization)
        if body.decision not in ("confirm", "reject"):
            raise APIError(400, "invalid_body")
        member = _family_child(conn, user["user_id"], family_id, member_id)
        if body.decision == "reject":
            reject_member(conn, member["id"], now=now, actor_user_id=user["user_id"])
            return {"id": str(member["id"]), "status": "removed"}
        fresh = confirm_member(conn, member["id"], now=now, actor_user_id=user["user_id"])
        phone = fresh.get("phone_e164")
        return {
            "id": str(member["id"]),
            "status": "active",
            "phone_last4": phone[-4:] if isinstance(phone, str) else None,
        }

    def _accept(conn, authorization, body: InviteAcceptIn) -> dict:
        now = _now()
        user = _user(conn, authorization)
        secret = normalize_invite(body.secret)
        if secret is None:
            raise APIError(400, "invite_invalid")
        member = accept_invite(
            conn, invite_hash=hash_invite(secret), user_id=user["user_id"], now=now
        )
        return {
            "member_id": str(member["id"]),
            "family_id": str(member["family_id"]),
            "display_name": member["display_name"],
            "status": "invited",
        }

    def _enrolling_child(conn, user_id) -> dict:
        member = child_membership(conn, user_id)
        if member is None:
            raise APIError(403, "not_a_child")
        return member

    def _otp_start(conn, authorization, body: OtpStartIn):
        now = _now()
        user = _user(conn, authorization)
        member = _enrolling_child(conn, user["user_id"])
        if member["status"] != "invited" or member["phone_e164"] is not None:
            raise APIError(409, "phone_already_set")
        phone = body.phone_e164
        phone_region(phone)
        code = otp_codes()
        expires_at = now + OTP_TTL
        start_phone_otp(
            conn,
            member["id"],
            phone,
            code_hash=hash_otp(phone, code),
            now=now,
            expires_at=expires_at,
            daily_limit=OTP_SENDS_PER_DAY,
        )
        payload = {
            "status": "sent",
            "phone_last4": phone[-4:],
            "expires_at": _iso(expires_at),
        }
        return payload, phone, code

    def _otp_check(conn, authorization, body: OtpCheckIn):
        now = _now()
        user = _user(conn, authorization)
        member = _enrolling_child(conn, user["user_id"])
        phone = body.phone_e164
        phone_region(phone)
        if member["phone_e164"] is not None:
            raise APIError(409, "phone_already_set")
        outcome = check_phone_otp(
            conn,
            member["id"],
            phone,
            matches=lambda stored: otp_matches(phone, body.code, stored),
            now=now,
            max_attempts=OTP_MAX_ATTEMPTS,
        )
        # A miss is committed: the attempt count is the brute-force guard.
        if outcome == "dead":
            return _fail(400, "otp_expired")
        if outcome == "wrong":
            return _fail(400, "otp_wrong")
        complete_phone_otp(conn, member["id"], phone, now=now)
        add_family_event(
            conn,
            member["family_id"],
            now=now,
            actor_user_id=user["user_id"],
            step="phone_verified",
        )
        return {"status": "verified", "phone_last4": phone[-4:]}

    def _dev_login(conn, body: DevLoginIn) -> dict:
        now = _now()
        name = _required_name(body.display_name)
        if body.locale not in ("en", "ko"):
            raise APIError(400, "invalid_body")
        if body.auth_subject is None:
            subject = "dev-" + str(uuid4())
        elif _SUBJECT.fullmatch(body.auth_subject) is None:
            raise APIError(400, "invalid_body")
        else:
            subject = body.auth_subject
        user_id = ensure_user(
            conn,
            auth_provider=_DEV_PROVIDER,
            auth_subject=subject,
            display_name=name,
            locale=body.locale,
            now=now,
        )
        token = _new_session(conn, user_id, now)
        return {
            "token": token,
            "user_id": str(user_id),
            "auth_subject": subject,
        }

    def _create_family(conn, authorization, body: FamilyIn) -> dict:
        now = _now()
        user = _user(conn, authorization)
        name = _required_name(body.name)
        rows = memberships_for_user(conn, user["user_id"])
        if any(row["role"] == "child" for row in rows):
            raise APIError(403, "not_a_parent")
        if any(row["role"] == "parent" for row in rows):
            raise APIError(409, "already_in_a_family")
        family_id = create_family(
            conn, name=name, created_by=user["user_id"], now=now
        )
        add_member(
            conn,
            family_id=family_id,
            role="parent",
            display_name=user["display_name"],
            now=now,
            user_id=user["user_id"],
            status="active",
        )
        return {"id": str(family_id), "name": name}

    def _add_child(conn, authorization, family_id: str, body: ChildIn) -> dict:
        now = _now()
        user = _user(conn, authorization)
        family = _uuid(family_id)
        if active_parent(conn, user["user_id"], family) is None:
            raise APIError(404, "not_found")
        name = _required_name(body.display_name)
        member_id = add_member(
            conn,
            family_id=family,
            role="child",
            display_name=name,
            now=now,
            status="invited",
        )
        invite = _new_invite(conn, member_id, family, user["user_id"], now, "child_invited")
        return {
            "id": str(member_id),
            "display_name": name,
            "status": "invited",
            **invite,
        }

    def _activate(conn, authorization, member_id: str, body: ActivateIn) -> dict:
        user = _user(conn, authorization)
        member = _child_for_parent(conn, user["user_id"], member_id)
        phone_region(body.phone_e164)
        mark_member_callable(
            conn,
            member["id"],
            body.phone_e164,
            now=_now(),
            user_id=body.user_id,
        )
        return {"status": "active", "phone_last4": body.phone_e164[-4:]}

    def _dev_check_code(conn, authorization, member_id: str, body: CheckCodeIn) -> dict:
        user = _user(conn, authorization)
        member = _child_for_parent(conn, user["user_id"], member_id)
        if member.get("user_id") is not None and member["user_id"] != user["user_id"]:
            raise APIError(403, "not_the_child")
        _store_code(conn, member["id"], body)
        return {"status": "set"}

    def _my_check_code(conn, authorization, body: CheckCodeIn) -> dict:
        user = _user(conn, authorization)
        children = [
            row
            for row in memberships_for_user(conn, user["user_id"])
            if row["role"] == "child"
        ]
        if len(children) != 1:
            raise APIError(403, "not_a_child")
        _store_code(conn, children[0]["id"], body)
        return {"status": "set"}

    def _store_code(conn, member_id, body: CheckCodeIn) -> None:
        set_check_code(
            conn,
            member_id,
            body.code,
            now=_now(),
            biometric_ok=body.biometric_ok,
            rng=rng,
        )

    def _open(conn, authorization, body: CaseIn):
        now = _now()
        user = _user(conn, authorization)
        member = member_contact(conn, body.child_member_id)
        if member is None:
            raise APIError(404, "not_found")
        if active_parent(conn, user["user_id"], member["family_id"]) is None:
            if member.get("user_id") == user["user_id"]:
                raise APIError(403, "not_a_parent")
            raise APIError(404, "not_found")
        if not child_callable(member):
            raise APIError(400, "member_not_callable")
        case_id = open_case(
            conn,
            family_id=member["family_id"],
            opened_by=user["user_id"],
            child_member_id=member["id"],
            parent_text=body.text,
            now=now,
        )
        view = apply_case(conn, case_id, "start", now=now, rng=rng)
        if view["result"] == "no_number":
            raise APIError(400, "member_not_callable")
        dial = None
        if view["state"] == "calling":
            fresh = member_contact(conn, member["id"])
            number = None if fresh is None else fresh.get("phone_e164")
            if isinstance(number, str) and number != "":
                attempt_id = record_call_attempt(conn, case_id, now=now)
                dial = (number, case_id, attempt_id)
        return _present(conn, view), dial

    def _after_dial(conn, case_id, attempt_id, ref, failed: bool) -> dict:
        now = _now()
        if failed:
            finish_call_attempt(conn, attempt_id, status="failed", now=now)
            view = apply_case(conn, case_id, "call_failed", now=now, rng=rng)
        else:
            finish_call_attempt(
                conn, attempt_id, status="sent", now=now, provider_ref=ref
            )
            view = apply_case(conn, case_id, "call_accepted", now=now, rng=rng)
        return _present(conn, view)

    def _call_code(conn, authorization, case_id: str) -> dict:
        now = _now()
        user = _user(conn, authorization)
        view = load_case(conn, _uuid(case_id), now=now)
        if _visible(conn, user["user_id"], view) != "child":
            raise APIError(403, "not_the_child")
        code = None
        if view["state"] == "calling" and view["code_channel"] == "one_time":
            code = call_code(conn, view["id"], now=now)
        if code is None:
            return {"code": None, "fallback": "static"}
        return {"code": code}

    def _get_case(conn, authorization, case_id: str) -> dict:
        user = _user(conn, authorization)
        view = load_case(conn, _uuid(case_id), now=_now())
        return _present(conn, view, _visible(conn, user["user_id"], view))

    def _answer(conn, authorization, case_id: str, body: AnswerIn) -> dict:
        now = _now()
        user = _user(conn, authorization)
        if body.answer not in ("yes", "no"):
            raise APIError(400, "invalid_body")
        case_uuid = _uuid(case_id)
        view = lock_case(conn, case_uuid, now=now)
        who = _visible(conn, user["user_id"], view)
        if who != "child":
            raise APIError(403, "not_the_child")
        if view["state"] in _TERMINAL:
            return _present(conn, view, "child")
        event = "push_answered_yes" if body.answer == "yes" else "push_answered_no"
        updated = apply_case(conn, case_uuid, event, now=now, rng=rng)
        return _present(conn, updated, "child")

    def _digits_route(conn, authorization, case_id: str, body: DigitsIn) -> dict:
        now = _now()
        user = _user(conn, authorization)
        case_uuid = _uuid(case_id)
        view = lock_case(conn, case_uuid, now=now)
        who = _visible(conn, user["user_id"], view)
        updated = apply_keypad(conn, case_uuid, body.digits, now=now, rng=rng)
        return _present(conn, updated, who)

    def _child_for_parent(conn, user_id, member_id: str) -> dict:
        member = member_contact(conn, _uuid(member_id))
        if member is None or member.get("role") != "child":
            raise APIError(404, "not_found")
        if active_parent(conn, user_id, member["family_id"]) is None:
            if member.get("user_id") == user_id:
                raise APIError(403, "not_a_parent")
            raise APIError(404, "not_found")
        return member

    return app


def _created(result):
    if isinstance(result, JSONResponse):
        return result
    return JSONResponse(result, status_code=201)


def _fail(status: int, code: str) -> JSONResponse:
    return JSONResponse({"error": code}, status_code=status)


def _from_value(exc: ValueError) -> tuple[int, str]:
    mapped = _VALUE_ERRORS.get(str(exc))
    if mapped is not None:
        return mapped
    if str(exc).startswith("now must be") or "timezone-aware" in str(exc):
        return 500, "config"
    log.error("rejected value: %s", type(exc).__name__)
    return 400, "invalid_body"


def _bearer(header: str | None) -> str | None:
    if not isinstance(header, str):
        return None
    kind, _, token = header.partition(" ")
    if kind != "Bearer" or token == "" or " " in token or len(token) > _TOKEN_LIMIT:
        return None
    return token


def _uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except (TypeError, ValueError):
        raise APIError(404, "not_found") from None


def _required_name(value: str) -> str:
    if not isinstance(value, str):
        raise APIError(400, "invalid_body")
    name = value.strip()
    if name == "" or len(name) > _NAME_LIMIT:
        raise APIError(400, "invalid_body")
    return name


def _iso(value) -> str | None:
    if value is None:
        return None
    return value.isoformat()
