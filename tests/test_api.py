"""Milestone 4: the product loop, with no handset and no socket.

Readings, where the milestone text allows more than one:

- Session lifetime is not specified. A token lasts 30 days. Expired and
  revoked tokens are 401, the same as a missing token. The hash is
  SHA-256. The plaintext is returned once by the dev login and is not a
  column.
- Dev login stores `auth_provider = apple` because the schema allows only
  apple and google. The subject is `dev-...` unless the caller passes one.
  It is not an Apple identity token. Milestone 5 replaces this route.
- Invite secrets and SMS OTP are milestone 5 (tests/test_enroll.py).
  Adding a child creates an invited row and, since milestone 5, returns
  the invite secret once. `POST /v1/dev/members/{id}/activate`
  exists only when DEV_AUTH=1. It sets opt-in, `phone_current_since`, and
  parent confirmation to the injected clock, and it does not send SMS.
- A call-channel yes is green only once that clock is 24 hours old. The
  scripted walk advances the injected clock by exactly 24 hours, which is
  the store's existing boundary. A yes before that is `number_recent`.
  A no on that call is still `not_sent`.
- The call-only check code is `POST /v1/dev/members/{id}/check-code`,
  because that child has no session. A parent cannot set a code on an
  app-linked child through it. `POST /v1/me/check-code` is the child only.
- Keypad posts go to `POST /v1/dev/cases/{id}/digits`, which calls
  `apply_keypad`. Twilio routes are not registered. A single folded digit
  while the case is still asking for a code is not a guess: the store
  would treat "1" as a static mismatch, and this layer does not hand it
  that digit. Spoken words are not answers.
- The parent's case JSON is an allowlist. The child's session gets a
  smaller one (`CHILD_CASE_KEYS`) with nothing from the suspicious message.
  Last4 only. No code, nonce, or hash. `color` is green, red, yellow, or
  open. `gather` is static, one_time, answer, or null.
- Names are stripped and refused when blank or longer than 200 characters.
  Parent text is capped at 8000 characters. Extra JSON keys are refused
  and the error body does not echo them.
- `boot` requires DATABASE_URL, CODE_PEPPER, and OTP_DERIVATION_KEY.
  CODE_WEBHOOK_SECRET stays on the hackathon webhook. DEV_AUTH is on only
  when the value is exactly `1`, and never when ENV=production.
- +1 means the NANP prefix. +82 is Korea. A well-formed number with any
  other prefix is `unsupported_country` and is not stored.
"""

import ast
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

import psycopg
import pytest
from fastapi.testclient import TestClient

from backend.api import (
    CHILD_CASE_KEYS,
    SESSION_TTL,
    InvalidPhone,
    RecordingCallProvider,
    UnsupportedCountry,
    apply_keypad,
    boot,
    color_of,
    create_app,
    gather_for,
    hash_token,
    keypad_action,
    phone_region,
    public_case,
)
from backend.store import add_member, apply_schema, call_code
from services.code_webhook import _digits, _yes_no


COMPOSE_COMMAND = "docker compose up -d"
TEST_SCHEMA = "familyshield_api_test"
NOW = datetime(2026, 11, 3, 3, 0, tzinfo=timezone.utc)
PEPPER = "test-pepper-0123456789"
DERIVATION_KEY = "test-derivation-key-0123456789"
ROOT_KEYS = {
    "id",
    "family_id",
    "child_member_id",
    "child_display_name",
    "state",
    "result",
    "color",
    "answered_via",
    "code_channel",
    "parent_text",
    "transcript",
    "claims",
    "pattern_id",
    "timeline",
    "phone_last4",
    "deadline_at",
    "created_at",
    "updated_at",
    "decided_at",
    "gather",
}
_phone_n = 0


def _database_url() -> str:
    value = __import__("os").environ.get("DATABASE_URL", "").strip()
    if value:
        return value
    return "postgresql://familyshield:familyshield@127.0.0.1:5432/familyshield"


def _skip_reason(error: BaseException) -> str:
    return (
        f"Postgres is not up ({type(error).__name__}: {error}). "
        f"Start it with: {COMPOSE_COMMAND}"
    )


def _connect(url: str) -> psycopg.Connection:
    connection = psycopg.connect(url, connect_timeout=3)
    connection.autocommit = True
    connection.execute(f"SET search_path TO {TEST_SCHEMA}")
    connection.autocommit = False
    return connection


def _wipe(connection) -> None:
    for table in (
        "case_events",
        "verification_attempts",
        "cases",
        "family_events",
        "phone_otp",
        "family_members",
        "families",
        "sessions",
        "users",
    ):
        connection.execute(f"DELETE FROM {table}")
    connection.commit()


class ManualClock:
    def __init__(self, now):
        self.current = now

    def now(self):
        return self.current

    def advance(self, delta):
        self.current = self.current + delta


@pytest.fixture(scope="session")
def database_url():
    url = _database_url()
    try:
        connection = psycopg.connect(url, connect_timeout=3)
    except Exception as exc:
        pytest.skip(_skip_reason(exc))
    connection.autocommit = True
    try:
        connection.execute(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE")
        connection.execute(f"CREATE SCHEMA {TEST_SCHEMA}")
        connection.execute(f"SET search_path TO {TEST_SCHEMA}")
        apply_schema(connection)
    finally:
        connection.close()
    return url


@pytest.fixture(autouse=True)
def secrets(monkeypatch):
    monkeypatch.setenv("CODE_PEPPER", PEPPER)
    monkeypatch.setenv("OTP_DERIVATION_KEY", DERIVATION_KEY)


@pytest.fixture
def world(database_url):
    provider = RecordingCallProvider()
    clock = ManualClock(NOW)
    issued = {"n": 0}

    def connect():
        return _connect(database_url)

    def tokens() -> str:
        issued["n"] += 1
        return f"session-secret-{issued['n']:04d}-" + ("x" * 24)

    app = create_app(
        connect=connect,
        clock=clock.now,
        rng=lambda n: b"\x42" * n,
        tokens=tokens,
        call_provider=provider,
        dev_auth=True,
    )
    connection = _connect(database_url)
    client = TestClient(app)
    try:
        yield client, clock, provider, connection
    finally:
        connection.rollback()
        _wipe(connection)
        connection.close()


def next_phone(country: str = "+1") -> str:
    global _phone_n
    _phone_n += 1
    if country == "+82":
        return f"+8210{_phone_n:08d}"
    return f"+1415{_phone_n:07d}"


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def login(client, name, locale="en", subject=None):
    body = {"display_name": name, "locale": locale}
    if subject is not None:
        body["auth_subject"] = subject
    response = client.post("/v1/dev/login", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def assert_absent(payload, secret: str) -> None:
    if secret and _found(payload, secret):
        raise AssertionError("a secret appeared in the response")


def _found(value, secret: str, key=None) -> bool:
    if key in {"id", "family_id", "child_member_id"}:
        return False
    if isinstance(value, str):
        return secret in value
    if isinstance(value, dict):
        return any(_found(item, secret, item_key) for item_key, item in value.items())
    if isinstance(value, list):
        return any(_found(item, secret) for item in value)
    return False


def _family(client, token, name="Kim") -> str:
    response = client.post("/v1/families", headers=auth(token), json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _child(client, token, family_id, name="민지") -> str:
    response = client.post(
        f"/v1/families/{family_id}/children",
        headers=auth(token),
        json={"display_name": name},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "invited"
    assert body["display_name"] == name
    assert len(body["invite_secret"]) == 14
    return body["id"]


def _activate(client, token, member_id, phone, user_id=None):
    body = {"phone_e164": phone}
    if user_id is not None:
        body["user_id"] = user_id
    response = client.post(
        f"/v1/dev/members/{member_id}/activate",
        headers=auth(token),
        json=body,
    )
    return response


def _set_dev_code(client, token, member_id, code, biometric_ok=False):
    return client.post(
        f"/v1/dev/members/{member_id}/check-code",
        headers=auth(token),
        json={"code": code, "biometric_ok": biometric_ok},
    )


def _open(client, token, member_id, text="please send money"):
    return client.post(
        "/v1/cases",
        headers=auth(token),
        json={"child_member_id": member_id, "text": text},
    )


def post_digits(client, token, case_id, digits):
    return client.post(
        f"/v1/dev/cases/{case_id}/digits",
        headers=auth(token),
        json={"digits": digits},
    )


def call_only(client, clock, *, advance=True, code="1357", text="please send money"):
    parent = login(client, "Parent")
    family_id = _family(client, parent["token"])
    member_id = _child(client, parent["token"], family_id)
    phone = next_phone()
    activated = _activate(client, parent["token"], member_id, phone)
    assert activated.status_code == 201, activated.text
    coded = _set_dev_code(client, parent["token"], member_id, code)
    assert coded.status_code == 200, coded.text
    if advance:
        clock.advance(timedelta(hours=24))
    opened = _open(client, parent["token"], member_id, text)
    assert opened.status_code == 201, opened.text
    return parent, member_id, phone, opened.json()


# --- Pure functions, no database ---


def test_phone_region_accepts_nanp_and_korea_only():
    assert phone_region("+14155550123") == "us"
    assert phone_region("+821012345678") == "kr"
    with pytest.raises(UnsupportedCountry):
        phone_region("+442079460958")
    with pytest.raises(InvalidPhone):
        phone_region("14155550123")
    with pytest.raises(InvalidPhone):
        phone_region("+82 10 1234 5678")


def test_public_case_drops_codes_the_full_number_and_the_nonce():
    case_id = UUID("11111111-1111-1111-1111-111111111111")
    view = {
        "id": case_id,
        "family_id": UUID("22222222-2222-2222-2222-222222222222"),
        "child_member_id": UUID("33333333-3333-3333-3333-333333333333"),
        "state": "calling",
        "result": None,
        "answered_via": None,
        "code_channel": "static",
        "parent_text": "please send money",
        "transcript": None,
        "claims": None,
        "pattern_id": None,
        "events": ["start"],
        "deadline_at": NOW,
        "created_at": NOW,
        "updated_at": NOW,
        "decided_at": None,
        "one_time_nonce": b"\x11" * 16,
        "one_time_code_hash": "ab" * 32,
        "code_hash": "$argon2id$v=19$secret",
        "phone_e164": "+14155550123",
    }
    body = public_case(view, child_name="민지", phone_last4="0123")
    assert set(body) == ROOT_KEYS - {"gather"}
    assert body["state"] == "calling"
    assert body["color"] == "open"
    assert body["phone_last4"] == "0123"
    rendered = str(body)
    assert "+14155550123" not in rendered
    assert "argon2id" not in rendered
    assert "one_time_nonce" not in body
    assert body["timeline"] == ["start"]


def test_colors_follow_the_state():
    assert color_of("confirmed") == "green"
    assert color_of("scam") == "red"
    assert color_of("not_confirmed") == "yellow"
    assert color_of("calling") == "open"
    assert gather_for({"state": "calling", "code_channel": "static"}) == "static"
    assert gather_for({"state": "awaiting_answer", "code_channel": "static"}) == "answer"
    assert gather_for({"state": "confirmed", "code_channel": "static"}) is None


def test_a_single_digit_before_the_code_is_not_a_guess():
    calling = {"state": "calling", "code_channel": "static"}
    assert keypad_action(calling, "1") == ("ignore", "1")
    assert keypad_action(calling, "१") == ("ignore", "1")
    assert keypad_action(calling, "*") == ("digits", "*")
    assert keypad_action(calling, "0000") == ("digits", "0000")
    assert keypad_action(calling, "२५८०") == ("digits", "2580")


def test_spoken_yes_is_not_a_keypad_yes():
    waiting = {"state": "awaiting_answer", "code_channel": "static"}
    assert keypad_action(waiting, "1") == ("answer_yes", "1")
    assert keypad_action(waiting, "１") == ("answer_yes", "1")
    assert keypad_action(waiting, "2") == ("answer_no", "2")
    assert keypad_action(waiting, "5") == ("answer_unclear", "5")
    assert keypad_action(waiting, "yes") == ("answer_unclear", "")
    assert keypad_action(waiting, "yeah") == ("answer_unclear", "")
    assert _yes_no("yeah") == "yes"
    assert keypad_action(waiting, "yeah")[0] != "answer_yes"
    assert keypad_action({"state": "confirmed"}, "1") == ("ignore", "1")


def test_keypad_folding_matches_the_webhook_helper():
    raw = "code २५८०!"
    assert keypad_action({"state": "calling"}, raw)[1] == _digits(raw)


def test_hash_token_is_not_the_token():
    token = "session-secret-" + "x" * 32
    digest = hash_token(token)
    assert digest != token
    assert len(digest) == 64
    assert token not in digest


def test_session_ttl_is_thirty_days():
    assert SESSION_TTL == timedelta(days=30)


def test_api_does_not_dial_or_read_the_clock_except_at_the_defaults():
    source = open("backend/api.py", encoding="utf-8").read()
    tree = ast.parse(source)
    imported = []
    stack = []

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            stack.append(node.name)
            self.generic_visit(node)
            stack.pop()

        def visit_Import(self, node):
            imported.extend(alias.name.split(".")[0] for alias in node.names)

        def visit_ImportFrom(self, node):
            if node.module:
                imported.append(node.module.split(".")[0])
            self.generic_visit(node)

        def visit_Call(self, node):
            if isinstance(node.func, ast.Attribute):
                allowed = {
                    "now": {"default_clock"},
                    "utcnow": set(),
                    "token_bytes": {"default_rng"},
                    "token_urlsafe": {"default_token"},
                    "randbelow": set(),
                }
                if node.func.attr in allowed:
                    assert stack and stack[-1] in allowed[node.func.attr]
            self.generic_visit(node)

    Visitor().visit(tree)
    used = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
    }
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert "_yes_no" not in used
    assert "_yes_no" not in imported_names
    assert "_digits" in imported_names
    for banned in ("socket", "twilio", "requests", "anthropic", "cartesia"):
        assert banned not in imported


def test_boot_refuses_dev_auth_in_production():
    with pytest.raises(RuntimeError, match="DEV_AUTH"):
        boot(
            {
                "ENV": "production",
                "DEV_AUTH": "1",
                "DATABASE_URL": "postgresql://example",
                "CODE_PEPPER": "pepper",
                "OTP_DERIVATION_KEY": "key",
            }
        )


@pytest.mark.parametrize(
    "missing",
    ["DATABASE_URL", "CODE_PEPPER", "OTP_DERIVATION_KEY"],
)
def test_boot_refuses_a_missing_secret(missing):
    env = {
        "ENV": "development",
        "DEV_AUTH": "1",
        "DATABASE_URL": "postgresql://example",
        "CODE_PEPPER": "pepper",
        "OTP_DERIVATION_KEY": "key",
    }
    env[missing] = "  "
    with pytest.raises(RuntimeError, match=missing):
        boot(env)


def _fake_prompts() -> str:
    """Twelve one-byte stand-ins, so a production boot test can pass the prompt check."""
    import tempfile
    from pathlib import Path

    from backend.calls import LANGUAGES, PROMPT_NAMES

    root = Path(tempfile.mkdtemp(prefix="fs-prompts-"))
    for language in LANGUAGES:
        (root / language).mkdir()
        for name in PROMPT_NAMES:
            (root / language / f"{name}.mp3").write_bytes(b"\x00")
    return str(root)


PRODUCTION_SIGN_IN = {
    "PUBLIC_BASE_URL": "https://api.example.com",
    "PROMPTS_DIR": _fake_prompts(),
    "APPLE_BUNDLE_ID": "com.example.familyshield",
    "GOOGLE_SERVER_CLIENT_ID": "example.apps.googleusercontent.com",
    "TWILIO_ACCOUNT_SID": "AC" + "0" * 32,
    "TWILIO_AUTH_TOKEN": "token",
    "TWILIO_FROM_NUMBER": "+14155550100",
}


def test_boot_leaves_dev_routes_out_of_production():
    app = boot(
        {
            "ENV": "production",
            "DEV_AUTH": "",
            "DATABASE_URL": "postgresql://example",
            "CODE_PEPPER": "pepper",
            "OTP_DERIVATION_KEY": "key",
            **PRODUCTION_SIGN_IN,
        }
    )
    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/v1/families" in paths
    assert "/v1/cases" in paths
    assert "/v1/dev/login" not in paths
    assert "/v1/dev/cases/{case_id}/digits" not in paths
    # Milestone 6: the signed Twilio webhooks are the production keypad path.
    assert "/voice/twilio/{kind}" in paths
    assert "/tools/verify_code" not in paths


def test_production_does_not_serve_the_generated_docs():
    app = boot(
        {
            "ENV": "production",
            "DEV_AUTH": "",
            "DATABASE_URL": "postgresql://example",
            "CODE_PEPPER": "pepper",
            "OTP_DERIVATION_KEY": "key",
            **PRODUCTION_SIGN_IN,
        }
    )
    client = TestClient(app)
    for path in ("/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404, path
    dev = boot(
        {
            "ENV": "development",
            "DEV_AUTH": "1",
            "DATABASE_URL": "postgresql://example",
            "CODE_PEPPER": "pepper",
            "OTP_DERIVATION_KEY": "key",
        }
    )
    assert TestClient(dev).get("/openapi.json").status_code == 200


def test_dev_auth_must_be_exactly_one():
    app = boot(
        {
            "ENV": "development",
            "DEV_AUTH": "true",
            "DATABASE_URL": "postgresql://example",
            "CODE_PEPPER": "pepper",
            "OTP_DERIVATION_KEY": "key",
            **PRODUCTION_SIGN_IN,
        }
    )
    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/v1/dev/login" not in paths


def test_recording_provider_formats_the_would_call_line_and_does_not_connect():
    provider = RecordingCallProvider()
    provider.place("+14155550123")
    assert provider.calls == ["would call +14155550123"]
    source = open("backend/api.py", encoding="utf-8").read()
    assert 'f"would call {phone_e164}"' in source


# --- The product loop ---


def test_call_only_child_static_code_then_one_is_confirmed(world):
    client, clock, provider, conn = world
    parent, member_id, phone, opened = call_only(client, clock)
    assert opened["state"] == "calling"
    assert opened["code_channel"] == "static"
    assert opened["result"] is None
    assert opened["gather"] == "static"
    assert opened["child_display_name"] == "민지"
    assert provider.calls == [f"would call {phone}"]
    user_id = conn.execute(
        "SELECT user_id FROM family_members WHERE id = %s",
        (member_id,),
    ).fetchone()[0]
    assert user_id is None
    case_id = opened["id"]
    coded = post_digits(client, parent["token"], case_id, "1357")
    assert coded.status_code == 200
    assert coded.json()["state"] == "awaiting_answer"
    assert coded.json()["gather"] == "answer"
    pressed = post_digits(client, parent["token"], case_id, "1")
    assert pressed.status_code == 200
    assert pressed.json()["state"] == "confirmed"
    assert pressed.json()["result"] == "sent"
    assert pressed.json()["answered_via"] == "call"
    assert pressed.json()["color"] == "green"
    assert pressed.json()["gather"] is None
    got = client.get(f"/v1/cases/{case_id}", headers=auth(parent["token"]))
    assert got.status_code == 200
    body = got.json()
    assert set(body) == ROOT_KEYS
    assert body["state"] == "confirmed"
    assert body["result"] == "sent"
    assert body["color"] == "green"
    assert body["phone_last4"] == phone[-4:]
    assert phone not in got.text
    assert_absent(body, "1357")
    stored = conn.execute(
        """
        SELECT m.code_hash, c.one_time_nonce, c.one_time_code_hash
        FROM cases AS c
        JOIN family_members AS m ON m.id = c.child_member_id
        WHERE c.id = %s
        """,
        (case_id,),
    ).fetchone()
    assert stored[0] not in got.text
    assert stored[1] is None
    attempts = conn.execute(
        """
        SELECT channel, status, provider, provider_ref
        FROM verification_attempts WHERE case_id = %s
        """,
        (case_id,),
    ).fetchall()
    assert attempts == [("call", "sent", "twilio", None)]
    assert len(provider.calls) == 1


def test_in_app_no_is_not_flipped_by_a_following_code(world):
    client, clock, provider, conn = world
    parent = login(client, "Parent")
    child = login(client, "Minji", locale="ko", subject="child-minji")
    family_id = _family(client, parent["token"])
    member_id = _child(client, parent["token"], family_id)
    phone = next_phone()
    activated = _activate(
        client, parent["token"], member_id, phone, user_id=child["user_id"]
    )
    assert activated.status_code == 201, activated.text
    opened = _open(client, parent["token"], member_id)
    assert opened.status_code == 201, opened.text
    body = opened.json()
    assert body["state"] == "calling"
    assert body["code_channel"] == "one_time"
    assert provider.calls == [f"would call {phone}"]
    case_id = body["id"]
    code = call_code(conn, UUID(case_id), now=clock.now())
    assert code is not None and len(code) == 6
    answer = client.post(
        f"/v1/cases/{case_id}/answer",
        headers=auth(child["token"]),
        json={"answer": "no"},
    )
    assert answer.status_code == 200
    assert answer.json()["state"] == "scam"
    assert answer.json()["result"] == "not_sent"
    assert answer.json()["answered_via"] == "push"
    assert answer.json()["color"] == "red"
    follow = post_digits(client, parent["token"], case_id, code)
    one = post_digits(client, parent["token"], case_id, "1")
    assert follow.json()["state"] == "scam"
    assert follow.json()["result"] == "not_sent"
    assert one.json()["state"] == "scam"
    assert one.json()["result"] == "not_sent"
    got = client.get(f"/v1/cases/{case_id}", headers=auth(parent["token"]))
    assert got.json()["state"] == "scam"
    assert got.json()["result"] == "not_sent"
    assert_absent(got.json(), code)
    child_view = client.get(f"/v1/cases/{case_id}", headers=auth(child["token"]))
    assert child_view.status_code == 200
    assert_absent(child_view.json(), code)
    assert phone not in got.text
    assert list(child_view.json()) == list(CHILD_CASE_KEYS)
    assert child_view.json()["kind"] == "money_request"
    assert list(answer.json()) == list(CHILD_CASE_KEYS)


def test_the_child_never_sees_the_suspicious_message(world):
    client, clock, _provider, _conn = world
    parent = login(client, "Parent")
    child = login(client, "Minji", subject="child-view")
    family_id = _family(client, parent["token"])
    member_id = _child(client, parent["token"], family_id)
    phone = next_phone()
    assert _activate(client, parent["token"], member_id, phone, child["user_id"]).status_code == 201
    clock.advance(timedelta(hours=24))
    story = "Mom I was arrested, send $3000 in gift cards, don't tell Dad"
    case_id = _open(client, parent["token"], member_id, story).json()["id"]
    parent_view = client.get(f"/v1/cases/{case_id}", headers=auth(parent["token"])).json()
    assert parent_view["parent_text"] == story
    child_view = client.get(f"/v1/cases/{case_id}", headers=auth(child["token"]))
    for leaked in (story, "gift cards", phone[-4:], "Kim"):
        assert leaked not in child_view.text
    for key in ("parent_text", "transcript", "claims", "pattern_id", "timeline",
                "phone_last4", "family_id", "child_display_name"):
        assert key not in child_view.json()


def test_digit_five_after_a_right_code_is_yellow_no_answer(world):
    client, _clock, _provider, _conn = world
    parent, _member, _phone, opened = call_only(client, _clock)
    case_id = opened["id"]
    assert post_digits(client, parent["token"], case_id, "1357").json()["gather"] == "answer"
    pressed = post_digits(client, parent["token"], case_id, "5")
    body = pressed.json()
    assert body["state"] == "not_confirmed"
    assert body["result"] == "no_answer"
    assert body["color"] == "yellow"
    assert body["answered_via"] is None
    assert body["gather"] is None


def test_one_wrong_static_code_is_yellow_and_has_no_further_gather(world):
    client, _clock, _provider, _conn = world
    parent, _member, _phone, opened = call_only(client, _clock)
    case_id = opened["id"]
    wrong = post_digits(client, parent["token"], case_id, "0000")
    body = wrong.json()
    assert body["state"] == "not_confirmed"
    assert body["result"] == "wrong"
    assert body["color"] == "yellow"
    assert body["gather"] is None
    assert "0000" not in wrong.text
    assert "static_code_mismatch" in body["timeline"]
    again = post_digits(client, parent["token"], case_id, "1357")
    assert again.json()["state"] == "not_confirmed"
    assert again.json()["result"] == "wrong"
    assert again.json()["gather"] is None
    assert again.json()["timeline"] == body["timeline"]
    assert "code_accepted" not in again.json()["timeline"]


def test_digit_one_before_any_code_stays_non_terminal(world):
    client, _clock, _provider, _conn = world
    parent, _member, _phone, opened = call_only(client, _clock)
    case_id = opened["id"]
    pressed = post_digits(client, parent["token"], case_id, "1")
    body = pressed.json()
    assert body["state"] == "calling"
    assert body["result"] is None
    assert body["gather"] == "static"
    assert body["state"] not in {"confirmed", "scam", "not_confirmed"}
    assert "static_code_mismatch" not in body["timeline"]
    assert "code_rejected" not in body["timeline"]


def test_a_call_yes_on_a_new_number_is_yellow_and_a_no_is_red(world):
    client, clock, _provider, _conn = world
    parent, _member, _phone, opened = call_only(client, clock, advance=False)
    case_id = opened["id"]
    post_digits(client, parent["token"], case_id, "1357")
    yes = post_digits(client, parent["token"], case_id, "1")
    assert yes.json()["state"] == "not_confirmed"
    assert yes.json()["result"] == "number_recent"
    assert yes.json()["color"] == "yellow"
    assert yes.json()["state"] != "confirmed"
    parent_b, _member_b, _phone_b, opened_b = call_only(client, clock, advance=False)
    case_b = opened_b["id"]
    post_digits(client, parent_b["token"], case_b, "1357")
    no = post_digits(client, parent_b["token"], case_b, "2")
    assert no.json()["state"] == "scam"
    assert no.json()["result"] == "not_sent"
    assert no.json()["color"] == "red"


def test_unsupported_country_stores_nothing(world):
    client, _clock, provider, conn = world
    parent = login(client, "Parent")
    family_id = _family(client, parent["token"])
    member_id = _child(client, parent["token"], family_id)
    response = _activate(client, parent["token"], member_id, "+442079460958")
    assert response.status_code == 400
    assert response.json() == {"error": "unsupported_country"}
    assert "+442079460958" not in response.text
    row = conn.execute(
        "SELECT phone_e164, phone_opted_in_at, status FROM family_members WHERE id = %s",
        (member_id,),
    ).fetchone()
    assert row == (None, None, "invited")
    assert provider.calls == []
    missing_plus = _activate(client, parent["token"], member_id, "14155550123")
    assert missing_plus.status_code == 400
    assert missing_plus.json() == {"error": "invalid_phone"}


def test_a_korean_number_is_accepted_and_would_be_called(world):
    client, clock, provider, conn = world
    parent = login(client, "Parent")
    family_id = _family(client, parent["token"])
    member_id = _child(client, parent["token"], family_id)
    phone = next_phone("+82")
    activated = _activate(client, parent["token"], member_id, phone)
    assert activated.status_code == 201
    assert activated.json()["phone_last4"] == phone[-4:]
    assert phone not in activated.text
    coded = _set_dev_code(client, parent["token"], member_id, "1357")
    assert coded.status_code == 200
    clock.advance(timedelta(hours=24))
    opened = _open(client, parent["token"], member_id)
    assert opened.status_code == 201
    assert opened.json()["code_channel"] == "static"
    assert provider.calls == [f"would call {phone}"]
    stored = conn.execute(
        "SELECT phone_e164, status FROM family_members WHERE id = %s",
        (member_id,),
    ).fetchone()
    assert stored == (phone, "active")


def test_a_number_inside_the_text_is_not_the_number_we_call(world):
    client, clock, provider, _conn = world
    parent, _member, phone, opened = call_only(
        client,
        clock,
        text="my new number is +19995550000 please wire it",
    )
    assert provider.calls == [f"would call {phone}"]
    assert "+19995550000" not in provider.calls[0]
    assert opened["parent_text"] == "my new number is +19995550000 please wire it"


def test_an_extra_phone_field_is_refused_and_not_echoed(world):
    client, _clock, provider, _conn = world
    parent = login(client, "Parent")
    family_id = _family(client, parent["token"])
    member_id = _child(client, parent["token"], family_id)
    phone = next_phone()
    assert _activate(client, parent["token"], member_id, phone).status_code == 201
    response = client.post(
        "/v1/cases",
        headers=auth(parent["token"]),
        json={
            "child_member_id": member_id,
            "text": "hi",
            "phone": "+19995550000",
        },
    )
    assert response.status_code == 400
    assert response.json() == {"error": "invalid_body"}
    assert "+19995550000" not in response.text
    assert "1357" not in response.text
    assert provider.calls == []


def test_invited_child_is_not_callable_and_no_case_is_stored(world):
    client, _clock, provider, conn = world
    parent = login(client, "Parent")
    family_id = _family(client, parent["token"])
    member_id = _child(client, parent["token"], family_id)
    response = _open(client, parent["token"], member_id)
    assert response.status_code == 400
    assert response.json() == {"error": "member_not_callable"}
    count = conn.execute("SELECT count(*) FROM cases").fetchone()[0]
    assert count == 0
    assert provider.calls == []


def test_child_cannot_open_a_case_and_parent_cannot_answer(world):
    client, clock, _provider, _conn = world
    parent = login(client, "Parent")
    child = login(client, "Minji", locale="ko", subject="child-answer")
    family_id = _family(client, parent["token"])
    member_id = _child(client, parent["token"], family_id)
    phone = next_phone()
    assert (
        _activate(
            client, parent["token"], member_id, phone, user_id=child["user_id"]
        ).status_code
        == 201
    )
    assert _set_dev_code(client, parent["token"], member_id, "1357").status_code == 403
    mine = client.post(
        "/v1/me/check-code",
        headers=auth(child["token"]),
        json={"code": "1357", "biometric_ok": False},
    )
    assert mine.status_code == 200
    assert mine.json() == {"status": "set"}
    assert "1357" not in mine.text
    clock.advance(timedelta(hours=24))
    denied = _open(client, child["token"], member_id)
    assert denied.status_code == 403
    assert denied.json() == {"error": "not_a_parent"}
    opened = _open(client, parent["token"], member_id)
    assert opened.status_code == 201
    case_id = opened.json()["id"]
    parent_answer = client.post(
        f"/v1/cases/{case_id}/answer",
        headers=auth(parent["token"]),
        json={"answer": "yes"},
    )
    assert parent_answer.status_code == 403
    assert parent_answer.json() == {"error": "not_the_child"}
    assert client.get(
        f"/v1/cases/{case_id}", headers=auth(parent["token"])
    ).json()["state"] == "calling"


def test_a_second_answer_does_not_move_the_case(world):
    client, clock, _provider, conn = world
    parent = login(client, "Parent")
    child = login(client, "Minji", locale="en", subject="child-idem")
    family_id = _family(client, parent["token"])
    member_id = _child(client, parent["token"], family_id)
    assert (
        _activate(
            client,
            parent["token"],
            member_id,
            next_phone(),
            user_id=child["user_id"],
        ).status_code
        == 201
    )
    opened = _open(client, parent["token"], member_id)
    case_id = opened.json()["id"]
    clock.advance(timedelta(seconds=1))
    first = client.post(
        f"/v1/cases/{case_id}/answer",
        headers=auth(child["token"]),
        json={"answer": "no"},
    )
    second = client.post(
        f"/v1/cases/{case_id}/answer",
        headers=auth(child["token"]),
        json={"answer": "yes"},
    )
    assert first.json()["state"] == "scam"
    assert second.json()["state"] == "scam"
    assert second.json()["result"] == "not_sent"
    assert second.json()["decided_at"] == first.json()["decided_at"]
    assert second.json()["updated_at"] == first.json()["updated_at"]
    steps = conn.execute(
        "SELECT step FROM case_events WHERE case_id = %s ORDER BY seq ASC",
        (case_id,),
    ).fetchall()
    assert [step for (step,) in steps] == ["start", "push_answered_no"]


def test_a_stranger_cannot_read_the_case(world):
    client, _clock, _provider, _conn = world
    parent, _member, _phone, opened = call_only(client, _clock)
    stranger = login(client, "Stranger", subject="stranger-1")
    response = client.get(
        f"/v1/cases/{opened['id']}",
        headers=auth(stranger["token"]),
    )
    assert response.status_code == 404
    assert response.json() == {"error": "not_found"}
    missing = client.get(
        "/v1/cases/not-a-uuid",
        headers=auth(parent["token"]),
    )
    assert missing.status_code == 404
    assert missing.json() == {"error": "not_found"}


def test_missing_and_expired_and_revoked_sessions_look_the_same(world):
    client, clock, _provider, conn = world
    parent = login(client, "Parent", subject="parent-expire")
    clock.advance(SESSION_TTL - timedelta(seconds=1))
    still = client.post(
        "/v1/families",
        headers=auth(parent["token"]),
        json={"name": "Kim"},
    )
    assert still.status_code == 201
    clock.advance(timedelta(seconds=1))
    expired = client.post(
        "/v1/families",
        headers=auth(parent["token"]),
        json={"name": "Other"},
    )
    assert expired.status_code == 401
    assert expired.json() == {"error": "unauthorized"}
    fresh = login(client, "Parent", subject="parent-expire")
    assert fresh["user_id"] == parent["user_id"]
    conn.execute(
        "UPDATE sessions SET revoked_at = %s WHERE token_hash = %s",
        (clock.now(), hash_token(fresh["token"])),
    )
    conn.commit()
    revoked = client.post(
        "/v1/families",
        headers=auth(fresh["token"]),
        json={"name": "Again"},
    )
    assert revoked.status_code == 401
    assert revoked.json() == {"error": "unauthorized"}
    naked = client.post("/v1/families", json={"name": "Kim"})
    assert naked.status_code == 401
    assert naked.json() == {"error": "unauthorized"}


def test_the_session_token_is_stored_only_as_a_hash(world):
    client, _clock, _provider, conn = world
    parent = login(client, "Parent", subject="parent-hash")
    rows = conn.execute(
        "SELECT token_hash FROM sessions WHERE user_id = %s",
        (parent["user_id"],),
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == hash_token(parent["token"])
    assert parent["token"] not in rows[0][0]
    again = login(client, "Renamed", subject="parent-hash")
    assert again["user_id"] == parent["user_id"]
    assert again["token"] != parent["token"]
    stored_name = conn.execute(
        "SELECT display_name FROM users WHERE id = %s",
        (parent["user_id"],),
    ).fetchone()[0]
    assert stored_name == "Parent"


def test_a_parent_cannot_open_a_second_family(world):
    client, _clock, _provider, _conn = world
    parent = login(client, "Parent")
    _family(client, parent["token"])
    again = client.post(
        "/v1/families",
        headers=auth(parent["token"]),
        json={"name": "Other"},
    )
    assert again.status_code == 409
    assert again.json() == {"error": "already_in_a_family"}


def test_a_linked_child_cannot_create_a_family(world):
    client, _clock, _provider, _conn = world
    parent = login(client, "Parent")
    child = login(client, "Minji", subject="child-family")
    family_id = _family(client, parent["token"])
    member_id = _child(client, parent["token"], family_id)
    assert (
        _activate(
            client,
            parent["token"],
            member_id,
            next_phone(),
            user_id=child["user_id"],
        ).status_code
        == 201
    )
    response = client.post(
        "/v1/families",
        headers=auth(child["token"]),
        json={"name": "Mine"},
    )
    assert response.status_code == 403
    assert response.json() == {"error": "not_a_parent"}


def test_replacing_a_check_code_requires_the_biometric_flag(world):
    client, clock, _provider, _conn = world
    parent, member_id, _phone, _opened = call_only(client, clock, code="1357")
    # The walk above already consumed the first case's call. Set a new code
    # and open a fresh case. The first set in call_only used biometric_ok false.
    refused = _set_dev_code(client, parent["token"], member_id, "2468", False)
    assert refused.status_code == 403
    assert refused.json() == {"error": "biometric_required"}
    assert "2468" not in refused.text
    replaced = _set_dev_code(client, parent["token"], member_id, "2468", True)
    assert replaced.status_code == 200
    assert replaced.json() == {"status": "set"}
    opened = _open(client, parent["token"], member_id)
    assert opened.status_code == 201
    case_id = opened.json()["id"]
    old = post_digits(client, parent["token"], case_id, "1357")
    assert old.json()["result"] == "wrong"
    fresh = _open(client, parent["token"], member_id)
    assert fresh.status_code == 201
    accepted = post_digits(client, parent["token"], fresh.json()["id"], "2468")
    assert accepted.json()["state"] == "awaiting_answer"
    assert accepted.json()["gather"] == "answer"


def test_parent_check_code_route_is_refused_and_a_bad_body_is_not_echoed(world):
    client, _clock, _provider, _conn = world
    parent = login(client, "Parent")
    _family(client, parent["token"])
    response = client.post(
        "/v1/me/check-code",
        headers=auth(parent["token"]),
        json={"code": "1357", "biometric_ok": False},
    )
    assert response.status_code == 403
    assert response.json() == {"error": "not_a_child"}
    echoed = client.post(
        "/v1/me/check-code",
        headers=auth(parent["token"]),
        json={"code": "1357", "biometric_ok": "nope", "leak": "1357"},
    )
    assert echoed.status_code == 400
    assert echoed.json() == {"error": "invalid_body"}
    assert "1357" not in echoed.text


def test_folded_digits_match_the_static_code(world):
    client, _clock, _provider, _conn = world
    parent, _member, _phone, opened = call_only(client, _clock)
    pressed = post_digits(client, parent["token"], opened["id"], "१३५७")
    assert pressed.json()["state"] == "awaiting_answer"
    assert pressed.json()["gather"] == "answer"
    assert "१३५७" not in pressed.text


def test_a_spoken_yes_after_the_code_stays_yellow(world):
    client, _clock, _provider, _conn = world
    parent, _member, _phone, opened = call_only(client, _clock)
    case_id = opened["id"]
    post_digits(client, parent["token"], case_id, "1357")
    spoken = post_digits(client, parent["token"], case_id, "yeah")
    assert spoken.json()["state"] == "not_confirmed"
    assert spoken.json()["result"] == "no_answer"
    assert spoken.json()["color"] == "yellow"


def test_an_empty_gather_after_the_code_is_not_a_no(world):
    client, _clock, _provider, _conn = world
    parent, _member, _phone, opened = call_only(client, _clock)
    case_id = opened["id"]
    post_digits(client, parent["token"], case_id, "1357")
    empty = post_digits(client, parent["token"], case_id, "")
    assert empty.json()["result"] == "no_answer"
    assert empty.json()["result"] != "not_sent"


def test_the_same_phone_cannot_be_activated_twice(world):
    client, _clock, _provider, conn = world
    parent = login(client, "Parent")
    family_id = _family(client, parent["token"])
    first = _child(client, parent["token"], family_id, name="민지")
    second = _child(client, parent["token"], family_id, name="Arjun")
    phone = next_phone()
    assert _activate(client, parent["token"], first, phone).status_code == 201
    conflict = _activate(client, parent["token"], second, phone)
    assert conflict.status_code == 409
    assert conflict.json() == {"error": "phone_in_use"}
    assert phone not in conflict.text
    row = conn.execute(
        "SELECT phone_e164 FROM family_members WHERE id = %s",
        (second,),
    ).fetchone()
    assert row[0] is None


def test_a_locked_static_code_does_not_dial(world):
    client, clock, provider, conn = world
    parent, member_id, phone, _opened = call_only(client, clock, advance=False)
    # call_only already placed one call and the code was set at the same
    # timestamp as a later guess would use. Step the clock so the mismatches
    # fall after code_set_at, which is what the lock counts.
    clock.advance(timedelta(seconds=1))
    # The case call_only opened is still in `calling`. Finish it with a wrong
    # code, then open four more, then the locked one.
    first = post_digits(client, parent["token"], _opened["id"], "0000")
    assert first.json()["result"] == "wrong"
    for _ in range(4):
        opened = _open(client, parent["token"], member_id)
        assert opened.status_code == 201
        assert opened.json()["state"] == "calling"
        done = post_digits(client, parent["token"], opened.json()["id"], "0000")
        assert done.json()["result"] == "wrong"
    assert provider.calls == [f"would call {phone}"] * 5
    # One parent may open 5 cases per child per day (milestone 15), so the
    # sixth comes from a second parent in the same family.
    other = login(client, "Second parent")
    family_id = conn.execute(
        "SELECT family_id FROM family_members WHERE id = %s", (UUID(member_id),)
    ).fetchone()[0]
    add_member(
        conn, family_id=family_id, role="parent", display_name="Second parent",
        now=clock.now(), user_id=UUID(other["user_id"]), status="active",
    )
    conn.commit()
    locked = _open(client, other["token"], member_id)
    assert locked.status_code == 201
    assert locked.json()["state"] == "not_confirmed"
    assert locked.json()["result"] == "code_locked"
    assert locked.json()["color"] == "yellow"
    assert locked.json()["gather"] is None
    assert provider.calls == [f"would call {phone}"] * 5


def test_a_missing_pepper_does_not_log_or_return_the_code(world, monkeypatch, caplog):
    client, _clock, _provider, _conn = world
    parent = login(client, "Parent")
    family_id = _family(client, parent["token"])
    # Adding a child hashes its invite with the pepper, so remove it after setup.
    member_id = _child(client, parent["token"], family_id)
    phone = next_phone()
    assert _activate(client, parent["token"], member_id, phone).status_code == 201
    monkeypatch.delenv("CODE_PEPPER", raising=False)
    caplog.set_level(logging.DEBUG)
    response = _set_dev_code(client, parent["token"], member_id, "1357")
    assert response.status_code == 500
    assert response.json() == {"error": "config"}
    assert "1357" not in response.text
    assert "1357" not in caplog.text
    assert parent["token"] not in caplog.text


def test_dev_routes_are_absent_without_the_flag(database_url):
    def connect():
        return _connect(database_url)

    app = create_app(
        connect=connect,
        clock=lambda: NOW,
        rng=lambda n: b"\x11" * n,
        tokens=lambda: "session-secret-" + "y" * 32,
        call_provider=RecordingCallProvider(),
        dev_auth=False,
    )
    client = TestClient(app)
    response = client.post(
        "/v1/dev/login",
        json={"display_name": "Parent", "locale": "en", "code": "1357"},
    )
    assert response.status_code == 404
    assert "1357" not in response.text
    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/v1/dev/cases/{case_id}/digits" not in paths
    assert "/v1/families" in paths


def test_apply_keypad_does_not_commit(database_url):
    connection = _connect(database_url)
    try:
        from backend.store import add_member, create_family, create_user, open_case, set_check_code

        parent = create_user(
            connection,
            auth_provider="apple",
            auth_subject="api-rollback",
            display_name="Parent",
            locale="en",
            now=NOW,
        )
        family = create_family(connection, name="Kim", created_by=parent, now=NOW)
        member = add_member(
            connection,
            family_id=family,
            role="child",
            display_name="민지",
            now=NOW,
            status="active",
            phone_e164=next_phone(),
            phone_opted_in_at=NOW - timedelta(days=2),
            phone_current_since=NOW - timedelta(days=2),
            confirmed_by_parent_at=NOW - timedelta(days=2),
        )
        set_check_code(
            connection,
            member,
            "1357",
            now=NOW - timedelta(days=2),
            biometric_ok=False,
            rng=lambda n: b"\x42" * n,
        )
        case_id = open_case(
            connection,
            family_id=family,
            opened_by=parent,
            child_member_id=member,
            parent_text="",
            now=NOW,
        )
        from backend.store import apply_case

        apply_case(
            connection,
            case_id,
            "start",
            now=NOW,
            rng=lambda n: b"\x42" * n,
        )
        updated = apply_keypad(connection, case_id, "1", now=NOW)
        assert updated["state"] == "calling"
        connection.rollback()
        check = _connect(database_url)
        try:
            count = check.execute("SELECT count(*) FROM cases").fetchone()[0]
            assert count == 0
        finally:
            check.close()
    finally:
        connection.rollback()
        _wipe(connection)
        connection.close()


def test_a_parent_cannot_be_linked_as_the_child(world):
    client, _clock, provider, conn = world
    parent = login(client, "Parent")
    family_id = _family(client, parent["token"])
    member_id = _child(client, parent["token"], family_id)
    phone = next_phone()
    response = _activate(
        client,
        parent["token"],
        member_id,
        phone,
        user_id=parent["user_id"],
    )
    assert response.status_code == 409
    assert response.json() == {"error": "already_in_a_family"}
    assert phone not in response.text
    row = conn.execute(
        "SELECT user_id, phone_e164, status FROM family_members WHERE id = %s",
        (member_id,),
    ).fetchone()
    assert row == (None, None, "invited")
    assert provider.calls == []


def test_an_unknown_locale_is_refused(world):
    client, _clock, _provider, _conn = world
    response = client.post(
        "/v1/dev/login",
        json={"display_name": "Parent", "locale": "fr"},
    )
    assert response.status_code == 400
    assert response.json() == {"error": "invalid_body"}
    assert "fr" not in response.text


def test_blank_names_are_refused(world):
    client, _clock, _provider, _conn = world
    parent = login(client, "Parent")
    response = client.post(
        "/v1/families",
        headers=auth(parent["token"]),
        json={"name": "   "},
    )
    assert response.status_code == 400
    assert response.json() == {"error": "invalid_body"}
