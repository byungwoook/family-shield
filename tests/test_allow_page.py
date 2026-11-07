"""Milestone 16: a call-only child, through an SMS link and a mobile web page.

Readings, where the milestone text allows more than one:

- The parent adds the child as usual, then submits the number they already
  had (`POST .../call-only`). That sets `confirmed_by_parent_at` and not
  `phone_opted_in_at`, drops the app invite, and texts the number a link.
- The link opens `/allow/{secret}`. A GET only shows the page, so a link
  preview cannot use it. "Allow" texts a 6-digit SMS code. The child types
  that code and the 4-digit check code twice; the check code is never
  rendered back. Success makes the child active and opted in, sets
  `phone_current_since`, and burns the link. The link lives 72 hours.
- `POST .../allow-link` sends a new link. Used after setup, it resets a
  forgotten code. The reset keeps `phone_current_since`.
- The SMS code here proves the number. It is never the code a verification
  call asks for: that is the 4-digit check code, on the static channel.
"""

import logging
import re
from datetime import timedelta
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from backend.api import create_app
from backend.calls import TwilioCalls, Voice
from backend.codes import verify_code
from backend.enroll import DevOtp
from test_api import (  # noqa: F401  (database_url and secrets are fixtures)
    NOW,
    ManualClock,
    _child,
    _connect,
    _fake_prompts,
    _family,
    _wipe,
    auth,
    database_url,
    login,
    next_phone,
    secrets,
)
from test_calls import BASE, TOKEN, FakeTwilioHttp, hook


LINK = re.compile(r"https://api\.example\.com(/allow/[A-Za-z0-9_-]+)")


@pytest.fixture
def world(database_url):
    clock = ManualClock(NOW)
    http = FakeTwilioHttp()
    voice = Voice(BASE)
    sms = DevOtp()
    issued = {"n": 0}

    def tokens():
        issued["n"] += 1
        return f"session-secret-{issued['n']:04d}-" + ("w" * 24)

    app = create_app(
        connect=lambda: _connect(database_url),
        clock=clock.now,
        rng=lambda n: b"\x42" * n,
        tokens=tokens,
        call_provider=TwilioCalls(
            account_sid="AC1", auth_token=TOKEN, from_number="+14155550100", voice=voice, post=http
        ),
        dev_auth=True,
        voice=voice,
        twilio_auth_token=TOKEN,
        prompts_dir=Path(_fake_prompts()),
        otp_sender=sms,
        public_base_url=BASE,
    )
    connection = _connect(database_url)
    try:
        yield {"client": TestClient(app), "clock": clock, "http": http, "sms": sms, "conn": connection}
    finally:
        connection.rollback()
        _wipe(connection)
        connection.close()


def added_by_parent(w, country="+1", name="Jun"):
    client = w["client"]
    parent = login(client, "Parent")
    family_id = _family(client, parent["token"])
    member_id = _child(client, parent["token"], family_id, name=name)
    phone = next_phone(country)
    response = client.post(
        f"/v1/families/{family_id}/members/{member_id}/call-only",
        headers=auth(parent["token"]), json={"phone_e164": phone},
    )
    assert response.status_code == 202, response.text
    assert response.json() == {"status": "link_sent", "phone_last4": phone[-4:]}
    return parent, family_id, member_id, phone


def last_link(w, phone):
    to, body = w["sms"].notices[-1]
    assert to == phone
    return LINK.search(body).group(1)


def allow(w, path, code="1357", again=None, otp=None):
    client = w["client"]
    form = client.post(f"{path}/otp")
    assert form.status_code == 200, form.text
    sent_otp = w["sms"].sent[-1][1]
    return client.post(f"{path}/confirm", data={
        "otp": sent_otp if otp is None else otp, "code": code, "again": code if again is None else again,
    })


def member(w, member_id):
    w["conn"].rollback()
    return w["conn"].execute(
        """
        SELECT status, user_id, phone_opted_in_at, phone_current_since, confirmed_by_parent_at,
               code_hash, code_salt, allow_hash, invite_hash
        FROM family_members WHERE id = %s
        """,
        (UUID(member_id),),
    ).fetchone()


def open_case(w, parent, member_id):
    return w["client"].post("/v1/cases", headers=auth(parent["token"]),
                            json={"child_member_id": member_id, "text": "money"})


# --- The parent's part ---


@pytest.mark.parametrize("country", ["+1", "+82"])
def test_the_parent_number_is_confirmed_but_not_an_opt_in(world, country):
    parent, _family_id, member_id, phone = added_by_parent(world, country)
    status, user_id, opted_in, since, confirmed, code_hash, _salt, allow_hash, invite_hash = member(world, member_id)
    assert (status, user_id, opted_in, since) == ("invited", None, None, None)
    assert confirmed == world["clock"].now()
    assert code_hash is None and invite_hash is None and allow_hash is not None
    _to, body = world["sms"].notices[-1]
    secret = LINK.search(body).group(1).rsplit("/", 1)[1]
    assert secret not in allow_hash
    assert ("인증번호" not in body) and not re.search(r"\b\d{4,6}\b", body.replace(phone, ""))
    if country == "+82":
        assert "패밀리 쉴드" in body
    blocked = open_case(world, parent, member_id)
    assert blocked.status_code == 400
    assert blocked.json() == {"error": "member_not_callable"}


def test_other_countries_and_app_children_are_refused(world):
    client = world["client"]
    parent = login(client, "Parent")
    family_id = _family(client, parent["token"])
    member_id = _child(client, parent["token"], family_id)
    uk = client.post(f"/v1/families/{family_id}/members/{member_id}/call-only",
                     headers=auth(parent["token"]), json={"phone_e164": "+442079460958"})
    assert uk.status_code == 400
    assert uk.json() == {"error": "unsupported_country"}
    assert world["sms"].notices == []
    kid = login(client, "Kid", subject="app-kid")
    secret = client.post(f"/v1/families/{family_id}/children", headers=auth(parent["token"]),
                         json={"display_name": "App kid"}).json()
    client.post("/v1/invites/accept", headers=auth(kid["token"]), json={"secret": secret["invite_secret"]})
    linked = client.post(f"/v1/families/{family_id}/members/{secret['id']}/call-only",
                         headers=auth(parent["token"]), json={"phone_e164": next_phone()})
    assert linked.status_code == 409
    assert linked.json() == {"error": "not_call_only"}


def test_a_number_someone_else_holds_is_refused(world):
    _p, _f, _m, phone = added_by_parent(world)
    client = world["client"]
    other = login(client, "Other", subject="other")
    family_id = _family(client, other["token"])
    member_id = _child(client, other["token"], family_id)
    taken = client.post(f"/v1/families/{family_id}/members/{member_id}/call-only",
                        headers=auth(other["token"]), json={"phone_e164": phone})
    assert taken.status_code == 409
    assert taken.json() == {"error": "phone_in_use"}


# --- The child's page ---


def test_the_page_opts_in_and_sets_the_code_without_showing_it(world, caplog):
    caplog.set_level(logging.DEBUG)
    parent, family_id, member_id, phone = added_by_parent(world, "+82", name="준")
    path = last_link(world, phone)
    page = world["client"].get(path)
    assert page.status_code == 200
    assert "준" in page.text and 'lang="ko"' in page.text
    assert "<script" not in page.text
    assert page.headers["cache-control"] == "no-store"
    assert page.headers["referrer-policy"] == "no-referrer"
    assert "default-src 'none'" in page.headers["content-security-policy"]
    assert world["client"].get(path).status_code == 200  # a preview does not use it up
    assert member(world, member_id)[0] == "invited"

    done = allow(world, path, code="1357")
    assert done.status_code == 200
    assert "1357" not in done.text
    assert "1357" not in caplog.text
    status, _uid, opted_in, since, _conf, code_hash, salt, allow_hash, _inv = member(world, member_id)
    assert (status, opted_in, since, allow_hash) == ("active", world["clock"].now(), world["clock"].now(), None)
    assert verify_code("1357", bytes(salt), code_hash)
    assert world["client"].get(path).status_code == 404
    roster = world["client"].get(f"/v1/families/{family_id}/members", headers=auth(parent["token"])).text
    assert "1357" not in roster
    steps = [r[0] for r in world["conn"].execute(
        "SELECT step FROM family_events WHERE family_id = %s ORDER BY seq", (UUID(family_id),)).fetchall()]
    assert steps[-1] == "call_only_allowed"


def test_the_check_code_must_match_and_a_typo_does_not_spend_the_sms_code(world):
    _parent, _family_id, member_id, phone = added_by_parent(world)
    path = last_link(world, phone)
    mismatch = allow(world, path, code="1357", again="1358")
    assert mismatch.status_code == 400
    assert "1357" not in mismatch.text and "1358" not in mismatch.text
    for bad in ("12a4", "123", "١٢٣٤"):
        response = world["client"].post(f"{path}/confirm", data={
            "otp": world["sms"].sent[-1][1], "code": bad, "again": bad})
        assert response.status_code == 400
    assert world["conn"].execute("SELECT max(attempts) FROM phone_otp").fetchone()[0] == 0
    ok = world["client"].post(f"{path}/confirm", data={
        "otp": world["sms"].sent[-1][1], "code": "2468", "again": "2468"})
    assert ok.status_code == 200
    assert member(world, member_id)[0] == "active"


def test_a_wrong_sms_code_is_refused_and_five_kill_it(world):
    _parent, _family_id, member_id, phone = added_by_parent(world)
    path = last_link(world, phone)
    world["client"].post(f"{path}/otp")
    real = world["sms"].sent[-1][1]
    wrong = f"{(int(real) + 1) % 1_000_000:06d}"
    for _ in range(5):
        response = world["client"].post(f"{path}/confirm", data={"otp": wrong, "code": "1357", "again": "1357"})
        assert response.status_code == 400
    dead = world["client"].post(f"{path}/confirm", data={"otp": real, "code": "1357", "again": "1357"})
    assert dead.status_code == 400
    assert member(world, member_id)[0] == "invited"
    retry = allow(world, path)
    assert retry.status_code == 200


def test_an_expired_link_does_nothing(world):
    _parent, _family_id, member_id, phone = added_by_parent(world)
    path = last_link(world, phone)
    world["clock"].advance(timedelta(hours=72))
    assert world["client"].get(path).status_code == 404
    assert world["client"].post(f"{path}/otp").status_code == 404
    assert world["sms"].sent == []
    assert world["client"].get("/allow/not-a-real-secret").status_code == 404


def test_too_many_sms_codes_in_a_day(world):
    _parent, _family_id, _member_id, phone = added_by_parent(world)
    path = last_link(world, phone)
    for _ in range(5):
        assert world["client"].post(f"{path}/otp").status_code == 200
    limited = world["client"].post(f"{path}/otp")
    assert limited.status_code == 429
    assert len(world["sms"].sent) == 5


# --- After setup ---


def test_cases_go_straight_to_the_static_call(world):
    client, clock = world["client"], world["clock"]
    parent, _family_id, member_id, phone = added_by_parent(world)
    allow(world, last_link(world, phone), code="1357")
    first_day = open_case(world, parent, member_id).json()
    assert (first_day["state"], first_day["code_channel"]) == ("calling", "static")
    sid = world["http"].sid()
    greeting = hook(client, "outbound", first_day["id"], CallSid=sid)
    assert "static_greeting.mp3" in greeting.text and 'numDigits="4"' in greeting.text
    # The SMS code proved the number. It is not what the call accepts.
    sms_code = world["sms"].sent[-1][1]
    refused = hook(client, "code", first_day["id"], CallSid=sid, Digits=sms_code)
    assert "question.mp3" not in refused.text and "code_failed.mp3" in refused.text
    second = open_case(world, parent, member_id).json()
    hook(client, "code", second["id"], CallSid=world["http"].sid(), Digits="1357")
    hook(client, "answer", second["id"], CallSid=world["http"].sid(), Digits="1")
    body = client.get(f"/v1/cases/{second['id']}", headers=auth(parent["token"])).json()
    assert body["result"] == "number_recent"
    clock.advance(timedelta(hours=24))
    third = open_case(world, parent, member_id).json()
    hook(client, "code", third["id"], CallSid=world["http"].sid(), Digits="1357")
    hook(client, "answer", third["id"], CallSid=world["http"].sid(), Digits="1")
    body = client.get(f"/v1/cases/{third['id']}", headers=auth(parent["token"])).json()
    assert (body["result"], body["color"]) == ("sent", "green")


def test_a_forgotten_code_is_reset_through_a_second_link(world):
    client, clock = world["client"], world["clock"]
    parent, family_id, member_id, phone = added_by_parent(world)
    allow(world, last_link(world, phone), code="1357")
    since = member(world, member_id)[3]
    clock.advance(timedelta(days=3))
    resent = client.post(f"/v1/families/{family_id}/members/{member_id}/allow-link",
                         headers=auth(parent["token"]))
    assert resent.status_code == 202
    reset = allow(world, last_link(world, phone), code="8642")
    assert reset.status_code == 200
    assert "8642" not in reset.text
    _s, _u, _o, new_since, _c, code_hash, salt, allow_hash, _i = member(world, member_id)
    assert new_since == since
    assert allow_hash is None
    assert verify_code("8642", bytes(salt), code_hash)
    assert not verify_code("1357", bytes(salt), code_hash)
    steps = [r[0] for r in world["conn"].execute(
        "SELECT step FROM family_events WHERE family_id = %s ORDER BY seq", (UUID(family_id),)).fetchall()]
    assert steps[-2:] == ["allow_link_sent", "call_only_code_reset"]


def test_only_this_familys_parent_can_send_a_link(world):
    client = world["client"]
    _parent, family_id, member_id, _phone = added_by_parent(world)
    other = login(client, "Other", subject="other-link")
    _family(client, other["token"])
    response = client.post(f"/v1/families/{family_id}/members/{member_id}/allow-link",
                           headers=auth(other["token"]))
    assert response.status_code == 404


def test_no_public_url_means_no_link(database_url):
    app = create_app(
        connect=lambda: _connect(database_url), clock=ManualClock(NOW).now,
        rng=lambda n: b"\x42" * n, tokens=lambda: "session-secret-0000-" + "q" * 24,
        call_provider=None, dev_auth=True, otp_sender=DevOtp(),
    )
    client = TestClient(app)
    connection = _connect(database_url)
    try:
        parent = login(client, "Parent")
        family_id = _family(client, parent["token"])
        member_id = _child(client, parent["token"], family_id)
        response = client.post(f"/v1/families/{family_id}/members/{member_id}/call-only",
                               headers=auth(parent["token"]), json={"phone_e164": next_phone()})
        assert response.status_code == 503
        assert response.json() == {"error": "allow_link_unavailable"}
    finally:
        _wipe(connection)
        connection.close()
