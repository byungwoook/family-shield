"""Milestone 8: push first, the call after 90 seconds, and the timers.

Readings, where the milestone text allows more than one:

- The push is one generic alert: a title, a fixed sentence in the child's
  locale, `kind=money_request`, and the case id. Nothing from the parent's
  text, the transcript, the claims, or either code.
- `tick` is the timer. It applies each passed deadline once, under the case
  lock, and then sends what the new state asks for. Production runs it in a
  loop (TIMER_SECONDS, default 5); tests call it after moving the clock.
- A push the provider calls dead (`permanent`) clears the token and applies
  `push_failed`: the call, or `unreachable` with no number. A `transient`
  failure, or no sender at all, waits for the 90-second window.
- A token belongs to one device: registering it on one child removes it from
  any other row. Registering sets the user's locale, which the alert uses.
"""

import json
import time
from datetime import timedelta
from uuid import UUID

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi.testclient import TestClient

from backend.api import RecordingCallProvider, create_app
from backend.push import (
    ALERT_BODY,
    GOOGLE_TOKEN_URL,
    PUSH_TTL_SECONDS,
    ApnsSender,
    FcmSender,
    PushRouter,
    RecordingPush,
    apns_payload,
    fcm_message,
    push_from_env,
)
from backend.store import add_member, call_code, create_user
from test_api import (  # noqa: F401  (database_url and secrets are fixtures)
    NOW,
    ManualClock,
    _activate,
    _child,
    _connect,
    _family,
    _wipe,
    auth,
    database_url,
    login,
    next_phone,
    secrets,
)


EC_KEY = ec.generate_private_key(ec.SECP256R1())
EC_PEM = EC_KEY.private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
).decode()
RSA_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
RSA_PEM = RSA_KEY.private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
).decode()


class Reply:
    def __init__(self, status, body=None):
        self.status_code = status
        self._body = body

    def json(self):
        if self._body is None:
            raise ValueError("no body")
        return self._body


class Recorder:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.requests = []

    def __call__(self, url, **kwargs):
        self.requests.append((url, kwargs))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


# --- Pure: payloads and senders ---


def test_the_alert_carries_nothing_from_the_case():
    for locale in ("en", "ko", None):
        payload = apns_payload("c-1", locale)
        assert set(payload) == {"aps", "kind", "case_id"}
        assert payload["kind"] == "money_request"
        assert set(payload["aps"]) == {"alert", "sound"}
        message = fcm_message("tok", "c-1", locale)["message"]
        assert set(message) == {"token", "notification", "data", "android"}
        assert message["data"] == {"kind": "money_request", "case_id": "c-1"}
    assert apns_payload("c", "ko")["aps"]["alert"]["body"] == ALERT_BODY["ko"]
    assert apns_payload("c", "fr")["aps"]["alert"]["body"] == ALERT_BODY["en"]
    for body in ALERT_BODY.values():
        assert not any(ch.isdigit() for ch in body)


def apns(post, clock=lambda: 1_700_000_000.0):
    return ApnsSender(
        team_id="TEAM123", key_id="KEY123", private_key=EC_PEM,
        topic="com.example.familyshield", post=post, clock=clock,
    )


def test_apns_request_shape():
    post = Recorder(Reply(200), Reply(200))
    sender = apns(post)
    assert sender.send(token="abc123", env="sandbox", locale="ko", case_id="c-1") == "sent"
    assert sender.send(token="abc123", env="production", locale="en", case_id="c-2") == "sent"
    (url1, first), (url2, second) = post.requests
    assert url1 == "https://api.sandbox.push.apple.com/3/device/abc123"
    assert url2 == "https://api.push.apple.com/3/device/abc123"
    headers = first["headers"]
    assert headers["apns-topic"] == "com.example.familyshield"
    assert headers["apns-push-type"] == "alert"
    assert headers["apns-expiration"] == str(1_700_000_000 + PUSH_TTL_SECONDS)
    token = headers["authorization"].removeprefix("bearer ")
    claims = jwt.decode(token, EC_KEY.public_key(), algorithms=["ES256"])
    assert claims == {"iss": "TEAM123", "iat": 1_700_000_000}
    assert jwt.get_unverified_header(token)["kid"] == "KEY123"
    assert second["headers"]["authorization"] == headers["authorization"]
    assert json.loads(first["content"]) == apns_payload("c-1", "ko")


@pytest.mark.parametrize(
    "reply, outcome",
    [
        (Reply(410, {"reason": "Unregistered"}), "permanent"),
        (Reply(400, {"reason": "BadDeviceToken"}), "permanent"),
        (Reply(400, {"reason": "DeviceTokenNotForTopic"}), "permanent"),
        (Reply(429, {"reason": "TooManyRequests"}), "transient"),
        (Reply(503), "transient"),
        (ConnectionError("down"), "transient"),
    ],
)
def test_apns_outcomes(reply, outcome):
    assert apns(Recorder(reply)).send(token="t", env="production", locale="en", case_id="c") == outcome


def test_apns_renews_its_provider_token_after_fifty_minutes():
    now = {"t": 1_700_000_000.0}
    post = Recorder(Reply(200), Reply(200))
    sender = apns(post, clock=lambda: now["t"])
    sender.send(token="t", env="production", locale="en", case_id="c")
    now["t"] += 51 * 60
    sender.send(token="t", env="production", locale="en", case_id="c")
    first, second = (r[1]["headers"]["authorization"] for r in post.requests)
    assert first != second


def fcm(post, clock=lambda: 1_700_000_000.0):
    return FcmSender(
        project_id="family-shield", client_email="push@family-shield.iam.gserviceaccount.com",
        private_key=RSA_PEM, post=post, clock=clock,
    )


def test_fcm_request_shape_and_token_cache():
    post = Recorder(
        Reply(200, {"access_token": "ya29.token", "expires_in": 3599}),
        Reply(200, {"name": "projects/x/messages/1"}),
        Reply(200, {"name": "projects/x/messages/2"}),
    )
    sender = fcm(post)
    assert sender.send(token="fcm-tok", locale="ko", case_id="c-1") == "sent"
    assert sender.send(token="fcm-tok", locale="en", case_id="c-2") == "sent"
    (token_url, token_request), (send_url, send_request), _third = post.requests
    assert token_url == GOOGLE_TOKEN_URL
    assertion = token_request["data"]["assertion"]
    claims = jwt.decode(
        assertion, RSA_KEY.public_key(), algorithms=["RS256"], audience=GOOGLE_TOKEN_URL,
        options={"verify_exp": False, "verify_iat": False},
    )
    assert claims["scope"] == "https://www.googleapis.com/auth/firebase.messaging"
    assert send_url == "https://fcm.googleapis.com/v1/projects/family-shield/messages:send"
    assert send_request["headers"]["Authorization"] == "Bearer ya29.token"
    assert send_request["json"] == fcm_message("fcm-tok", "c-1", "ko")
    assert len(post.requests) == 3


@pytest.mark.parametrize(
    "reply, outcome",
    [
        (Reply(404, {"error": {"status": "NOT_FOUND"}}), "permanent"),
        (Reply(400, {"error": {"status": "INVALID_ARGUMENT", "details": [
            {"@type": "type.googleapis.com/google.firebase.fcm.v1.FcmError", "errorCode": "UNREGISTERED"}]}}),
         "permanent"),
        (Reply(429, {"error": {"status": "RESOURCE_EXHAUSTED"}}), "transient"),
        (Reply(503), "transient"),
        (ConnectionError("down"), "transient"),
    ],
)
def test_fcm_outcomes(reply, outcome):
    post = Recorder(Reply(200, {"access_token": "a", "expires_in": 3600}), reply)
    assert fcm(post).send(token="t", locale="en", case_id="c") == outcome


def test_a_refused_fcm_access_token_is_transient():
    assert fcm(Recorder(Reply(401, {"error": "invalid_grant"}))).send(
        token="t", locale="en", case_id="c"
    ) == "transient"


def test_the_router_picks_by_provider():
    apns_side, fcm_side = RecordingPush(), RecordingPush()
    router = PushRouter(apns=apns_side, fcm=fcm_side)
    router.send(provider="apns", token="a", env="sandbox", locale="en", case_id="c")
    router.send(provider="fcm", token="f", env=None, locale="en", case_id="c")
    assert [s["token"] for s in apns_side.sent] == ["a"]
    assert [s["token"] for s in fcm_side.sent] == ["f"]
    assert PushRouter(apns=apns_side).send(
        provider="fcm", token="f", env=None, locale="en", case_id="c"
    ) == "transient"
    assert push_from_env(lambda name: "") is None


# --- Against the API ---


@pytest.fixture
def world(database_url):
    clock = ManualClock(NOW)
    calls = RecordingCallProvider()
    push = RecordingPush()
    issued = {"n": 0}

    def tokens():
        issued["n"] += 1
        return f"session-secret-{issued['n']:04d}-" + ("p" * 24)

    def build(sender=push, timer_seconds=None):
        return create_app(
            connect=lambda: _connect(database_url),
            clock=clock.now,
            rng=lambda n: b"\x42" * n,
            tokens=tokens,
            call_provider=calls,
            dev_auth=True,
            push_sender=sender,
            timer_seconds=timer_seconds,
        )

    app = build()
    connection = _connect(database_url)
    try:
        yield {
            "app": app, "client": TestClient(app), "build": build, "clock": clock,
            "calls": calls, "push": push, "conn": connection,
        }
    finally:
        connection.rollback()
        _wipe(connection)
        connection.close()


def register(client, token, *, provider="apns", device="device-token-1", env="sandbox", locale="ko"):
    return client.post(
        "/v1/me/push-token", headers=auth(token),
        json={"provider": provider, "token": device, "env": env, "locale": locale},
    )


def pushable_child(w, country="+1", provider="apns", subject="child-push"):
    client = w["client"]
    parent = login(client, "Parent")
    child = login(client, "Minji", subject=subject)
    family_id = _family(client, parent["token"])
    member_id = _child(client, parent["token"], family_id)
    phone = next_phone(country)
    assert _activate(client, parent["token"], member_id, phone, child["user_id"]).status_code == 201
    env = "sandbox" if provider == "apns" else None
    assert register(client, child["token"], provider=provider, env=env).status_code == 200
    w["clock"].advance(timedelta(hours=24))
    return parent, child, member_id, phone


def open_case(w, parent, member_id, text="Send $3000 in gift cards tonight"):
    response = w["client"].post(
        "/v1/cases", headers=auth(parent["token"]),
        json={"child_member_id": member_id, "text": text},
    )
    assert response.status_code == 201, response.text
    return response.json()


def attempts(w, case_id):
    """The attempts as a sorted list: a push and its follow-up call can share a timestamp."""
    w["conn"].rollback()
    return sorted(w["conn"].execute(
        "SELECT channel, status, provider FROM verification_attempts WHERE case_id = %s",
        (UUID(case_id),),
    ).fetchall())


def view(w, parent, case_id):
    return w["client"].get(f"/v1/cases/{case_id}", headers=auth(parent["token"])).json()


def test_a_child_with_a_token_gets_a_push_and_no_call(world):
    parent, _child_user, member_id, _phone = pushable_child(world)
    case = open_case(world, parent, member_id)
    assert case["state"] == "waiting_push"
    assert world["calls"].calls == []
    assert len(world["push"].sent) == 1
    sent = world["push"].sent[0]
    assert sent["provider"] == "apns" and sent["env"] == "sandbox"
    payload = json.dumps(sent["payload"], ensure_ascii=False)
    for leaked in ("3000", "gift", "Minji", "Parent", "민지"):
        assert leaked not in payload
    assert sent["payload"]["case_id"] == case["id"]
    assert sent["payload"]["aps"]["alert"]["body"] == ALERT_BODY["ko"]
    assert attempts(world, case["id"]) == [("push", "sent", "apns")]


@pytest.mark.parametrize("country", ["+1", "+82"])
def test_ninety_seconds_without_an_answer_places_exactly_one_call(world, country):
    parent, child, member_id, phone = pushable_child(world, country=country)
    case = open_case(world, parent, member_id)
    world["clock"].advance(timedelta(seconds=89))
    assert world["app"].state.tick() == 0
    assert view(world, parent, case["id"])["state"] == "waiting_push"
    world["clock"].advance(timedelta(seconds=1))
    assert world["app"].state.tick() == 1
    body = view(world, parent, case["id"])
    assert (body["state"], body["code_channel"]) == ("calling", "one_time")
    assert world["calls"].calls == [f"would call {phone}"]
    assert world["app"].state.tick() == 0
    assert world["calls"].calls == [f"would call {phone}"]
    assert attempts(world, case["id"]) == [("call", "sent", "twilio"), ("push", "superseded", "apns")]
    code = call_code(world["conn"], UUID(case["id"]), now=world["clock"].now())
    assert code is not None
    assert code not in json.dumps(world["push"].sent)
    assert len(world["push"].sent) == 1


def test_an_in_app_answer_while_waiting_wins_and_no_call_follows(world):
    client = world["client"]
    parent, child, member_id, _phone = pushable_child(world)
    case = open_case(world, parent, member_id)
    answered = client.post(
        f"/v1/cases/{case['id']}/answer", headers=auth(child["token"]), json={"answer": "yes"}
    )
    assert answered.json()["result"] == "sent"
    world["clock"].advance(timedelta(seconds=120))
    assert world["app"].state.tick() == 0
    body = view(world, parent, case["id"])
    assert (body["state"], body["result"], body["answered_via"]) == ("confirmed", "sent", "push")
    assert world["calls"].calls == []


def test_a_dead_token_goes_straight_to_the_call_and_is_forgotten(world):
    world["push"].outcomes = ["permanent"]
    parent, _child_user, member_id, phone = pushable_child(world)
    case = open_case(world, parent, member_id)
    assert case["state"] == "calling"
    assert world["calls"].calls == [f"would call {phone}"]
    assert attempts(world, case["id"]) == [("call", "sent", "twilio"), ("push", "failed", "apns")]
    token = world["conn"].execute(
        "SELECT push_token FROM family_members WHERE id = %s", (UUID(member_id),)
    ).fetchone()[0]
    assert token is None
    assert "push_failed" in view(world, parent, case["id"])["timeline"]


def test_a_dead_token_with_no_phone_is_unreachable(world):
    client, conn, clock = world["client"], world["conn"], world["clock"]
    parent = login(client, "Parent")
    family_id = _family(client, parent["token"])
    child_user = create_user(
        conn, auth_provider="google", auth_subject="push-only", display_name="Jun",
        locale="en", now=clock.now(),
    )
    member_id = add_member(
        conn, family_id=UUID(family_id), role="child", display_name="Jun", now=clock.now(),
        user_id=child_user, status="active", push_token="only-token", push_provider="fcm",
        confirmed_by_parent_at=clock.now(),
    )
    conn.commit()
    world["push"].outcomes = ["permanent"]
    case = open_case(world, parent, str(member_id))
    assert (case["state"], case["result"], case["color"]) == ("not_confirmed", "unreachable", "yellow")
    assert world["calls"].calls == []


@pytest.mark.parametrize("sender", ["transient", None])
def test_an_undelivered_push_waits_for_the_window(world, sender):
    if sender == "transient":
        world["push"].outcomes = ["transient"]
        client = world["client"]
        app = world["app"]
    else:
        app = world["build"](sender=None)
        client = TestClient(app)
        world["client"] = client
    parent, _child_user, member_id, phone = pushable_child(world)
    case = open_case(world, parent, member_id)
    assert case["state"] == "waiting_push"
    assert attempts(world, case["id"]) == [("push", "failed", "apns")]
    world["clock"].advance(timedelta(seconds=90))
    assert app.state.tick() == 1
    assert world["calls"].calls == [f"would call {phone}"]


def test_the_code_and_answer_windows_end_the_call_yellow(world):
    client, clock = world["client"], world["clock"]
    parent = login(client, "Parent")
    family_id = _family(client, parent["token"])
    first = _child(client, parent["token"], family_id, name="A")
    second = _child(client, parent["token"], family_id, name="B")
    for member_id in (first, second):
        assert _activate(client, parent["token"], member_id, next_phone()).status_code == 201
        client.post(
            f"/v1/dev/members/{member_id}/check-code", headers=auth(parent["token"]),
            json={"code": "1357", "biometric_ok": False},
        )
    clock.advance(timedelta(hours=24))
    silent = open_case(world, parent, first)
    coded = open_case(world, parent, second)
    client.post(f"/v1/dev/cases/{coded['id']}/digits", headers=auth(parent["token"]), json={"digits": "1357"})
    clock.advance(timedelta(seconds=45))
    assert world["app"].state.tick() == 1
    assert view(world, parent, coded["id"])["result"] == "no_answer"
    assert view(world, parent, silent["id"])["state"] == "calling"
    clock.advance(timedelta(seconds=135))
    assert world["app"].state.tick() == 1
    body = view(world, parent, silent["id"])
    assert (body["result"], body["color"]) == ("timeout", "yellow")
    assert body["timeline"][-1] == "code_window_elapsed"


def test_the_background_loop_runs_tick(world):
    app = world["build"](timer_seconds=0.05)
    world["client"] = TestClient(app)
    with world["client"]:
        parent, _child_user, member_id, phone = pushable_child(world)
        open_case(world, parent, member_id)
        world["clock"].advance(timedelta(seconds=91))
        deadline = time.monotonic() + 5
        while not world["calls"].calls and time.monotonic() < deadline:
            time.sleep(0.05)
    assert world["calls"].calls == [f"would call {phone}"]


# --- Token registration ---


def test_token_registration_needs_a_membership_and_is_validated(world):
    client = world["client"]
    stranger = login(client, "Nobody")
    assert register(client, stranger["token"]).status_code == 403
    parent = login(client, "Parent")
    _family(client, parent["token"])
    # Milestone 15: a parent's device gets number-change notices.
    assert register(client, parent["token"], device="parent-device").status_code == 200
    _parent, child, member_id, _phone = pushable_child(world)
    for bad in (
        {"provider": "apns", "env": None},
        {"provider": "apns", "env": "staging"},
        {"provider": "fcm", "env": "sandbox"},
        {"provider": "webpush", "env": None},
        {"provider": "apns", "env": "sandbox", "device": "has space"},
        {"provider": "apns", "env": "sandbox", "locale": "fr"},
    ):
        args = {"device": "tok", "locale": "en", **bad}
        response = register(client, child["token"], provider=args["provider"], device=args["device"],
                            env=args["env"], locale=args["locale"])
        assert response.status_code == 400, bad
    assert register(client, child["token"], provider="fcm", env=None, device="fcm-1", locale="en").json() == {
        "status": "registered", "provider": "fcm"
    }
    row = world["conn"].execute(
        """
        SELECT m.push_provider, m.push_token, m.push_env, u.locale
        FROM family_members m JOIN users u ON u.id = m.user_id WHERE m.id = %s
        """,
        (UUID(member_id),),
    ).fetchone()
    assert row == ("fcm", "fcm-1", None, "en")


def test_a_token_moves_with_its_device(world):
    client, conn = world["client"], world["conn"]
    _p1, first, first_member, _ = pushable_child(world, subject="first-child")
    _p2, second, second_member, _ = pushable_child(world, subject="second-child")
    assert register(client, first["token"], device="shared").status_code == 200
    assert register(client, second["token"], device="shared").status_code == 200
    conn.rollback()
    rows = dict(conn.execute(
        "SELECT id, push_token FROM family_members WHERE id IN (%s, %s)",
        (UUID(first_member), UUID(second_member)),
    ).fetchall())
    assert rows == {UUID(first_member): None, UUID(second_member): "shared"}
