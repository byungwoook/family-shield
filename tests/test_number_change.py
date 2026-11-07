"""Milestone 15: number changes, case caps, and the 24-hour rule.

Readings, where the milestone text allows more than one:

- A number change is the same OTP routes, from a child who is already
  active: the start needs `biometric_ok` (the device check), and a correct
  code stores `pending_phone_e164`. The old number stays the dial target
  until a parent confirms on `POST /v1/families/{f}/members/{m}/phone-change`.
- The confirm is one transaction: every open case for that child ends
  `timeout` with the step `phone_number_changed`, the number moves, and
  `phone_current_since` restarts. The next call speaks the new number's
  language.
- Requesting and confirming each push the parents and the child's device
  (`number_change_requested` / `number_change_confirmed`, no number in the
  text) and text the number being replaced. That SMS has no code.
- Caps: 5 cases per parent per child and 10 per parent in a rolling 24 hours.
  Over the cap: 429 `rate_limited`, nothing stored, nothing dialed.
- The static lock (five mismatches in 24 hours) is the milestone 3 rule.
  These tests check it from the API: a wrong one-time code does not count,
  and a new check code clears it.
"""

import json
from datetime import timedelta
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from backend.api import create_app
from backend.calls import TwilioCalls, Voice
from backend.enroll import DevOtp
from backend.push import RecordingPush
from backend.store import add_member, call_code, load_case
from test_api import (  # noqa: F401  (database_url and secrets are fixtures)
    NOW,
    ManualClock,
    _activate,
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


@pytest.fixture
def world(database_url):
    clock = ManualClock(NOW)
    http = FakeTwilioHttp()
    voice = Voice(BASE)
    sms = DevOtp()
    push = RecordingPush()
    issued = {"n": 0}

    def tokens():
        issued["n"] += 1
        return f"session-secret-{issued['n']:04d}-" + ("n" * 24)

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
        push_sender=push,
    )
    connection = _connect(database_url)
    try:
        yield {
            "client": TestClient(app), "clock": clock, "http": http, "sms": sms,
            "push": push, "conn": connection, "app": app,
        }
    finally:
        connection.rollback()
        _wipe(connection)
        connection.close()


def family_with_child(w, country="+1", *, app_child=True, subject="nc-child"):
    client = w["client"]
    parent = login(client, "Parent", subject=f"parent-of-{subject}")
    child = login(client, "Minji", subject=subject) if app_child else None
    family_id = _family(client, parent["token"])
    member_id = _child(client, parent["token"], family_id)
    phone = next_phone(country)
    user_id = child["user_id"] if child else None
    assert _activate(client, parent["token"], member_id, phone, user_id).status_code == 201
    if child:
        coded = client.post("/v1/me/check-code", headers=auth(child["token"]),
                            json={"code": "2468", "biometric_ok": False})
    else:
        coded = client.post(f"/v1/dev/members/{member_id}/check-code", headers=auth(parent["token"]),
                            json={"code": "2468", "biometric_ok": False})
    assert coded.status_code == 200
    w["clock"].advance(timedelta(hours=24, minutes=1))
    return parent, child, family_id, member_id, phone


def request_change(w, child, new_phone, *, biometric=True):
    client = w["client"]
    started = client.post("/v1/phones/otp", headers=auth(child["token"]),
                          json={"phone_e164": new_phone, "biometric_ok": biometric})
    if started.status_code != 202:
        return started
    code = w["sms"].sent[-1][1]
    return client.post("/v1/phones/otp/check", headers=auth(child["token"]),
                       json={"phone_e164": new_phone, "code": code})


def decide(w, parent, family_id, member_id, decision):
    return w["client"].post(
        f"/v1/families/{family_id}/members/{member_id}/phone-change",
        headers=auth(parent["token"]), json={"decision": decision},
    )


def open_case(w, parent, member_id):
    return w["client"].post("/v1/cases", headers=auth(parent["token"]),
                            json={"child_member_id": member_id, "text": "money please"})


def dialed(w):
    return [kwargs["data"]["To"] for _url, kwargs in w["http"].requests]


def member_row(w, member_id):
    w["conn"].rollback()
    return w["conn"].execute(
        """
        SELECT phone_e164, pending_phone_e164, phone_current_since
        FROM family_members WHERE id = %s
        """,
        (UUID(member_id),),
    ).fetchone()


def steps(w, family_id):
    w["conn"].rollback()
    return [row[0] for row in w["conn"].execute(
        "SELECT step FROM family_events WHERE family_id = %s ORDER BY seq", (UUID(family_id),)
    ).fetchall()]


# --- The change itself ---


def test_a_change_needs_the_biometric_and_a_different_number(world):
    _parent, child, _family_id, _member_id, phone = family_with_child(world)
    no_bio = request_change(world, child, next_phone(), biometric=False)
    assert no_bio.status_code == 403
    assert no_bio.json() == {"error": "biometric_required"}
    same = request_change(world, child, phone)
    assert same.status_code == 409
    assert same.json() == {"error": "same_number"}


def test_the_new_number_waits_for_a_parent_and_is_not_called(world):
    client = world["client"]
    parent, child, family_id, member_id, phone = family_with_child(world)
    new_phone = next_phone("+82")
    checked = request_change(world, child, new_phone)
    assert checked.status_code == 200
    assert checked.json() == {"status": "pending_parent", "phone_last4": new_phone[-4:]}
    assert member_row(world, member_id)[:2] == (phone, new_phone)
    roster = client.get(f"/v1/families/{family_id}/members", headers=auth(parent["token"])).json()
    kid = next(m for m in roster["members"] if m["id"] == member_id)
    assert kid["pending_phone_last4"] == new_phone[-4:]
    assert kid["phone_last4"] == phone[-4:]
    assert open_case(world, parent, member_id).status_code == 201
    assert dialed(world) == [phone]


def test_request_and_confirm_each_notify_parents_child_and_the_old_number(world):
    client = world["client"]
    parent, child, family_id, member_id, phone = family_with_child(world)
    for token, device in ((parent["token"], "parent-device"), (child["token"], "child-device")):
        assert client.post("/v1/me/push-token", headers=auth(token), json={
            "provider": "fcm", "token": device, "env": None, "locale": "ko"}).status_code == 200
    new_phone = next_phone()
    request_change(world, child, new_phone)
    code_sent = world["sms"].sent[-1][1]
    requested = [p for p in world["push"].sent if p["kind"] == "number_change_requested"]
    assert sorted(p["token"] for p in requested) == ["child-device", "parent-device"]
    assert world["sms"].notices[-1][0] == phone
    assert decide(world, parent, family_id, member_id, "confirm").status_code == 200
    confirmed = [p for p in world["push"].sent if p["kind"] == "number_change_confirmed"]
    assert sorted(p["token"] for p in confirmed) == ["child-device", "parent-device"]
    assert [n[0] for n in world["sms"].notices] == [phone, phone]
    for _to, body in world["sms"].notices:
        assert code_sent not in body
        assert not any(ch.isdigit() for ch in body)
    for push in requested + confirmed:
        text = json.dumps(push["payload"], ensure_ascii=False)
        assert new_phone[-4:] not in text and phone[-4:] not in text
        assert push["payload"]["message"]["data"]["kind"].startswith("number_change")
    assert steps(world, family_id)[-2:] == ["number_change_requested", "number_change_confirmed"]


def test_confirm_moves_the_number_and_ends_open_cases(world):
    client, clock = world["client"], world["clock"]
    parent, child, family_id, member_id, phone = family_with_child(world)
    in_flight = open_case(world, parent, member_id).json()
    new_phone = next_phone()
    request_change(world, child, new_phone)
    clock.advance(timedelta(minutes=2))
    confirmed = decide(world, parent, family_id, member_id, "confirm")
    assert confirmed.json() == {
        "id": member_id, "status": "changed", "phone_last4": new_phone[-4:], "cancelled_cases": 1,
    }
    body = client.get(f"/v1/cases/{in_flight['id']}", headers=auth(parent["token"])).json()
    assert (body["state"], body["result"]) == ("not_confirmed", "timeout")
    assert body["timeline"][-1] == "phone_number_changed"
    late = hook(client, "code", in_flight["id"], CallSid=world["http"].sid(0), Digits="2468")
    assert "<Hangup/>" in late.text and "<Gather" not in late.text
    assert member_row(world, member_id) == (new_phone, None, clock.now())
    assert open_case(world, parent, member_id).status_code == 201
    assert dialed(world) == [phone, new_phone]


@pytest.mark.parametrize("old, new, language", [("+1", "+82", "ko"), ("+82", "+1", "en")])
def test_the_next_call_speaks_the_new_numbers_language(world, old, new, language):
    client = world["client"]
    parent, child, family_id, member_id, _phone = family_with_child(world, country=old)
    request_change(world, child, next_phone(new))
    decide(world, parent, family_id, member_id, "confirm")
    case = open_case(world, parent, member_id).json()
    outbound = hook(client, "outbound", case["id"], CallSid=world["http"].sid())
    assert f"/voice/prompts/{language}/one_time_greeting.mp3" in outbound.text


def test_reject_keeps_the_old_number(world):
    parent, child, family_id, member_id, phone = family_with_child(world)
    request_change(world, child, next_phone())
    rejected = decide(world, parent, family_id, member_id, "reject")
    assert rejected.json() == {"id": member_id, "status": "kept"}
    assert member_row(world, member_id)[:2] == (phone, None)
    assert steps(world, family_id)[-1] == "number_change_rejected"
    again = decide(world, parent, family_id, member_id, "confirm")
    assert again.status_code == 409
    assert again.json() == {"error": "no_pending_number"}


def test_only_this_familys_parent_decides(world):
    parent, child, family_id, member_id, _phone = family_with_child(world)
    request_change(world, child, next_phone())
    assert decide(world, child, family_id, member_id, "confirm").status_code == 404
    other = login(world["client"], "Other parent", subject="other-parent")
    _family(world["client"], other["token"])
    assert decide(world, other, family_id, member_id, "confirm").status_code == 404


def test_a_number_another_member_holds_cannot_be_the_new_number(world):
    _p1, _c1, _f1, _m1, taken = family_with_child(world, subject="first")
    _p2, child, _f2, _m2, _phone = family_with_child(world, subject="second")
    response = request_change(world, child, taken)
    assert response.status_code == 409
    assert response.json() == {"error": "phone_in_use"}


# --- The 24-hour rule after a change ---


def changed_child(w):
    parent, child, family_id, member_id, _phone = family_with_child(w)
    request_change(w, child, next_phone())
    decide(w, parent, family_id, member_id, "confirm")
    return parent, child, member_id


def answer_by_call(w, parent, member_id, digit):
    client = w["client"]
    case = open_case(w, parent, member_id).json()
    sid = w["http"].sid()
    code = call_code(w["conn"], UUID(case["id"]), now=w["clock"].now())
    w["conn"].rollback()
    hook(client, "code", case["id"], CallSid=sid, Digits=code)
    hook(client, "answer", case["id"], CallSid=sid, Digits=digit)
    return client.get(f"/v1/cases/{case['id']}", headers=auth(parent["token"])).json()


def test_a_call_yes_inside_24_hours_of_the_change_is_yellow(world):
    parent, _kid, member_id = changed_child(world)
    body = answer_by_call(world, parent, member_id, "1")
    assert (body["result"], body["color"]) == ("number_recent", "yellow")


def test_a_call_no_inside_24_hours_is_still_red(world):
    parent, _kid, member_id = changed_child(world)
    body = answer_by_call(world, parent, member_id, "2")
    assert (body["result"], body["color"]) == ("not_sent", "red")


def test_a_push_yes_inside_24_hours_stays_green(world):
    client = world["client"]
    parent, child, member_id = changed_child(world)
    client.post("/v1/me/push-token", headers=auth(child["token"]), json={
        "provider": "apns", "token": "dev-1", "env": "sandbox", "locale": "en"})
    case = open_case(world, parent, member_id).json()
    assert case["state"] == "waiting_push"
    answered = client.post(f"/v1/cases/{case['id']}/answer", headers=auth(child["token"]),
                           json={"answer": "yes"})
    assert answered.json()["result"] == "sent"


def test_a_call_yes_after_24_hours_is_green_again(world):
    parent, _kid, member_id = changed_child(world)
    world["clock"].advance(timedelta(hours=24))
    body = answer_by_call(world, parent, member_id, "1")
    assert (body["result"], body["color"]) == ("sent", "green")


# --- Caps ---


def test_the_sixth_case_for_one_child_in_a_day_is_refused(world):
    parent, _kid, _family_id, member_id, _phone = family_with_child(world)
    for _ in range(5):
        assert open_case(world, parent, member_id).status_code == 201
    calls_before = len(world["http"].requests)
    sixth = open_case(world, parent, member_id)
    assert sixth.status_code == 429
    assert sixth.json() == {"error": "rate_limited"}
    assert len(world["http"].requests) == calls_before
    assert world["conn"].execute("SELECT count(*) FROM cases").fetchone()[0] == 5
    world["clock"].advance(timedelta(hours=24))
    assert open_case(world, parent, member_id).status_code == 201


def test_ten_cases_per_parent_per_day(world):
    client = world["client"]
    parent, _kid, family_id, first, _phone = family_with_child(world, app_child=False)
    others = []
    for name in ("B", "C"):
        member_id = _child(client, parent["token"], family_id, name=name)
        assert _activate(client, parent["token"], member_id, next_phone()).status_code == 201
        client.post(f"/v1/dev/members/{member_id}/check-code", headers=auth(parent["token"]),
                    json={"code": "2468", "biometric_ok": False})
        others.append(member_id)
    world["clock"].advance(timedelta(hours=24, minutes=1))
    for member_id in (first, others[0]):
        for _ in range(5):
            assert open_case(world, parent, member_id).status_code == 201
    eleventh = open_case(world, parent, others[1])
    assert eleventh.status_code == 429


# --- The static lock, from the API ---


def second_parent(w, family_id, subject):
    other = login(w["client"], "Second parent", subject=subject)
    add_member(w["conn"], family_id=UUID(family_id), role="parent", display_name="Second",
               now=w["clock"].now(), user_id=UUID(other["user_id"]), status="active")
    w["conn"].commit()
    return other


def test_wrong_one_time_codes_do_not_count_toward_the_lock(world):
    client = world["client"]
    parent, _kid, family_id, member_id, _phone = family_with_child(world)
    for _ in range(5):
        case = open_case(world, parent, member_id).json()
        hook(client, "code", case["id"], CallSid=world["http"].sid(), Digits="000000")
    other = second_parent(world, family_id, "second-parent-ot")
    case = open_case(world, other, member_id).json()
    assert load_case(world["conn"], UUID(case["id"]), now=world["clock"].now())["static_locked"] is False
    world["conn"].rollback()
    switched = hook(client, "code", case["id"], CallSid=world["http"].sid(), Digits="")
    assert 'numDigits="4"' in switched.text


def test_a_new_check_code_clears_the_lock(world):
    client, clock = world["client"], world["clock"]
    parent, _kid, family_id, member_id, _phone = family_with_child(world, app_child=False)
    for _ in range(5):
        clock.advance(timedelta(seconds=1))
        case = open_case(world, parent, member_id).json()
        hook(client, "code", case["id"], CallSid=world["http"].sid(), Digits="0000")
    other = second_parent(world, family_id, "second-parent-static")
    locked = open_case(world, other, member_id).json()
    assert (locked["state"], locked["result"]) == ("not_confirmed", "code_locked")
    calls_before = len(world["http"].requests)
    reset = client.post(f"/v1/dev/members/{member_id}/check-code", headers=auth(parent["token"]),
                        json={"code": "1357", "biometric_ok": True})
    assert reset.status_code == 200
    clock.advance(timedelta(seconds=1))
    reopened = open_case(world, other, member_id).json()
    assert reopened["state"] == "calling"
    assert len(world["http"].requests) == calls_before + 1
