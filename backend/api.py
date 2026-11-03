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
login and the helpers that skip SMS exist only in that mode. Apple,
Google, invite secrets, and SMS OTP are later milestones.

`GET /v1/cases/{id}` is an allowlist. It has no code, no nonce, no hash,
and no full phone number. `phone_last4` is the only phone fragment, for
both the parent and the child. The call-code route is a later milestone.
"""

import hashlib
import logging
import os
import re
import secrets
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from backend.codes import (
    BiometricRequired,
    CodeConfigError,
    DerivationKeyError,
)
from backend.store import (
    CaseNotFound,
    PhoneInUse,
    active_parent,
    add_member,
    apply_case,
    create_family,
    create_session,
    ensure_user,
    load_case,
    lock_case,
    mark_member_callable,
    member_contact,
    memberships_for_user,
    open_case,
    record_call_attempt,
    session_user,
    set_check_code,
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


class DevLoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str = Field(max_length=_NAME_LIMIT)
    locale: str
    auth_subject: str | None = None


class RecordingCallProvider:
    """Records `would call {e164}`. Does not open a socket."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def place(self, phone_e164: str) -> None:
        if not isinstance(phone_e164, str) or phone_e164 == "":
            raise ValueError("phone_e164 is required")
        self.calls.append(f"would call {phone_e164}")


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

    def connect():
        import psycopg

        return psycopg.connect(database_url)

    return create_app(
        connect=connect,
        clock=default_clock,
        rng=default_rng,
        tokens=default_token,
        call_provider=RecordingCallProvider(),
        dev_auth=get("DEV_AUTH") == "1",
    )


def create_app(
    *,
    connect: Callable,
    clock: Callable[[], datetime],
    rng: Callable[[int], bytes],
    tokens: Callable[[], str],
    call_provider,
    dev_auth: bool,
) -> FastAPI:
    """Routes for one product process. Dependencies are injected."""
    app = FastAPI(title="Family Shield")

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

    def _present(conn, view: dict) -> dict:
        member = member_contact(conn, view["child_member_id"])
        phone = None if member is None else member.get("phone_e164")
        last4 = phone[-4:] if isinstance(phone, str) and len(phone) >= 4 else None
        name = member["display_name"] if member else ""
        body = public_case(view, child_name=name, phone_last4=last4)
        body["gather"] = gather_for(view)
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
        payload, phone = result
        if phone is not None:
            try:
                call_provider.place(phone)
            except Exception as exc:
                log.error("call provider failed: %s", type(exc).__name__)
        return JSONResponse(payload, status_code=201)

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
        return {
            "id": str(member_id),
            "display_name": name,
            "status": "invited",
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
        phone = None
        if view["state"] == "calling":
            fresh = member_contact(conn, member["id"])
            number = None if fresh is None else fresh.get("phone_e164")
            if isinstance(number, str) and number != "":
                record_call_attempt(conn, case_id, now=now)
                phone = number
        return _present(conn, view), phone

    def _get_case(conn, authorization, case_id: str) -> dict:
        user = _user(conn, authorization)
        view = load_case(conn, _uuid(case_id), now=_now())
        _visible(conn, user["user_id"], view)
        return _present(conn, view)

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
            return _present(conn, view)
        event = "push_answered_yes" if body.answer == "yes" else "push_answered_no"
        updated = apply_case(conn, case_uuid, event, now=now, rng=rng)
        return _present(conn, updated)

    def _digits_route(conn, authorization, case_id: str, body: DigitsIn) -> dict:
        now = _now()
        user = _user(conn, authorization)
        case_uuid = _uuid(case_id)
        view = lock_case(conn, case_uuid, now=now)
        _visible(conn, user["user_id"], view)
        updated = apply_keypad(conn, case_uuid, body.digits, now=now, rng=rng)
        return _present(conn, updated)

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
