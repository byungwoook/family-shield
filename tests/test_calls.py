"""Milestone 6: the Twilio keypad fallback call, +1 and +82, with no handset.

Readings, where the milestone text allows more than one:

- Twilio is faked at the HTTP layer: `TwilioCalls` gets a `post` that
  records the request and returns a CallSid. Webhooks are signed with the
  same scheme Twilio uses. `SIGNATURE_VECTOR` was computed with Twilio's
  own `RequestValidator`, so the scheme is pinned to theirs, not to ours.
- Every webhook must match the CallSid stored for that case. A signed
  request for another call changes nothing and hangs up.
- Every gather posts even when empty. On the one-time gather, star and
  silence both arrive as `Digits=""` and switch to the static code, which
  is not a guess. Silence on the static gather hangs up with no verdict.
- Final call status: `no-answer` and `busy` are `timeout`, `failed` and
  `canceled` are `call_failed`, and `completed` before an answer is
  `timeout` (code not entered) or `no_answer` (code entered). None of them
  is ever `not_sent`.
- The twelve mp3 files are not rendered yet (they need CARTESIA_API_KEY).
  The test that they are checked in is skipped until they are, and a boot
  outside DEV_AUTH=1 refuses to start without them.
"""

import logging
import re
import xml.etree.ElementTree as ET
from datetime import timedelta
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from backend.api import RecordingCallProvider, boot, create_app
from backend.calls import (
    LANGUAGES,
    PROMPT_LINES,
    PROMPT_NAMES,
    CallPlaceFailed,
    TwilioCalls,
    Voice,
    call_language,
    missing_prompts,
    twilio_signature,
    valid_signature,
)
from test_api import (  # noqa: F401  (database_url and secrets are fixtures)
    NOW,
    PRODUCTION_SIGN_IN,
    ManualClock,
    _activate,
    _child,
    _connect,
    _family,
    _set_dev_code,
    _wipe,
    _fake_prompts,
    auth,
    database_url,
    login,
    next_phone,
    secrets,
)


BASE = "https://api.example.com"
TOKEN = "tw-token"
SIGNATURE_VECTOR = (
    "tw-token",
    "https://api.example.com/voice/twilio/code?case_id=0b6f9c2e-1111-4222-8333-444455556666",
    {"CallSid": "CA" + "1" * 32, "Digits": "", "From": "+14155550100", "To": "+821012345678"},
    "ZpJOBJz0nDV/H02n2gCqBecbc+s=",
)


class FakeTwilioHttp:
    def __init__(self, status=201):
        self.status = status
        self.requests = []

    def __call__(self, url, **kwargs):
        self.requests.append((url, kwargs))
        n = len(self.requests)

        class Reply:
            status_code = self.status

            def json(_self):
                return {"sid": f"CA{n:032x}"}

        return Reply()

    def sid(self, index=-1):
        return f"CA{(len(self.requests) if index == -1 else index + 1):032x}"


# --- Pure: language, TwiML, signatures, the REST call ---


def test_call_language_follows_the_number_only():
    assert call_language("+821012345678") == "ko"
    assert call_language("+14155550123") == "en"
    for other in ("+442079460958", "", None, "821012345678"):
        with pytest.raises(ValueError):
            call_language(other)


def test_prompt_lines_match_the_design_doc_word_for_word():
    doc = Path("docs/PRODUCT_REDESIGN.md").read_text(encoding="utf-8")
    rows = re.findall(r'^\| `(\w+)\.mp3` \| [^|]+ \| "([^"]+)" \| "([^"]+)" \|$', doc, re.M)
    assert {name for name, _en, _ko in rows} == set(PROMPT_NAMES)
    for name, english, korean in rows:
        assert PROMPT_LINES["en"][name] == english
        assert PROMPT_LINES["ko"][name] == korean


def test_the_greetings_disclose_an_ai_and_no_line_has_a_placeholder():
    for language in LANGUAGES:
        for greeting in ("one_time_greeting", "static_greeting"):
            line = PROMPT_LINES[language][greeting]
            assert "AI" in line or "인공지능" in line
        for line in PROMPT_LINES[language].values():
            assert "{" not in line and "$" not in line


@pytest.mark.skipif(
    bool(missing_prompts()),
    reason="prompt mp3s not rendered yet: python -m scripts.render_prompts (needs CARTESIA_API_KEY)",
)
def test_the_twelve_prompt_files_are_checked_in():
    assert missing_prompts() == []


def parse(xml: str) -> ET.Element:
    root = ET.fromstring(xml)
    assert root.tag == "Response"
    assert root.find(".//Say") is None
    assert root.find(".//Record") is None
    return root


def test_one_time_gather_shape():
    voice = Voice(BASE)
    root = parse(voice.code_gather("c1", "en", "one_time", "one_time_greeting"))
    gather = root.find("Gather")
    assert gather.attrib == {
        "input": "dtmf",
        "numDigits": "6",
        "finishOnKey": "*",
        "timeout": "15",
        "actionOnEmptyResult": "true",
        "action": f"{BASE}/voice/twilio/code?case_id=c1",
        "method": "POST",
    }
    assert gather.find("Play").text == f"{BASE}/voice/prompts/en/one_time_greeting.mp3"
    assert [child.tag for child in root] == ["Gather", "Hangup"]


def test_static_and_answer_gathers_have_no_finish_key():
    voice = Voice(BASE)
    static = parse(voice.code_gather("c1", "ko", "static", "static_greeting")).find("Gather")
    assert static.attrib["numDigits"] == "4"
    assert static.attrib["finishOnKey"] == ""
    assert static.find("Play").text.endswith("/voice/prompts/ko/static_greeting.mp3")
    answer = parse(voice.question("c1", "ko")).find("Gather")
    assert answer.attrib["numDigits"] == "1"
    assert answer.attrib["finishOnKey"] == ""
    assert answer.attrib["action"] == f"{BASE}/voice/twilio/answer?case_id=c1"


def test_play_and_hang_up():
    root = parse(Voice(BASE).play_and_hang_up("en", "code_failed"))
    assert [child.tag for child in root] == ["Play", "Hangup"]
    with pytest.raises(ValueError):
        Voice(BASE).prompt_url("en", "anything_else")
    with pytest.raises(ValueError):
        Voice(BASE).prompt_url("fr", "thanks")


def test_signature_matches_twilios_request_validator():
    token, url, params, expected = SIGNATURE_VECTOR
    assert twilio_signature(token, url, params) == expected
    assert valid_signature(token, url, params, expected)
    assert not valid_signature(token, url + "x", params, expected)
    assert not valid_signature(token, url, {**params, "Digits": "1"}, expected)
    assert not valid_signature("other", url, params, expected)
    assert not valid_signature(token, url, params, None)
    assert not valid_signature("", url, params, expected)


def test_twilio_calls_places_one_unrecorded_call():
    http = FakeTwilioHttp()
    calls = TwilioCalls(
        account_sid="AC1", auth_token="t", from_number="+14155550100", voice=Voice(BASE), post=http
    )
    sid = calls.place("+821012345678", case_id="c-1")
    assert sid == http.sid()
    url, kwargs = http.requests[0]
    assert url == "https://api.twilio.com/2010-04-01/Accounts/AC1/Calls.json"
    assert kwargs["data"] == {
        "To": "+821012345678",
        "From": "+14155550100",
        "Url": f"{BASE}/voice/twilio/outbound?case_id=c-1",
        "Method": "POST",
        "StatusCallback": f"{BASE}/voice/twilio/status?case_id=c-1",
        "StatusCallbackMethod": "POST",
        "Timeout": "30",
        "Record": "false",
    }
    assert kwargs["auth"] == ("AC1", "t")


def test_twilio_calls_refuses_other_countries_and_bad_replies():
    http = FakeTwilioHttp(status=400)
    calls = TwilioCalls(
        account_sid="AC1", auth_token="t", from_number="+14155550100", voice=Voice(BASE), post=http
    )
    with pytest.raises(ValueError):
        calls.place("+442079460958", case_id="c")
    assert http.requests == []
    with pytest.raises(CallPlaceFailed) as caught:
        calls.place("+14155550123", case_id="c")
    assert "+14155550123" not in str(caught.value)


# --- Boot ---


def _production(**overrides):
    env = {
        "ENV": "production",
        "DATABASE_URL": "postgresql://example",
        "CODE_PEPPER": "p",
        "OTP_DERIVATION_KEY": "k",
        **PRODUCTION_SIGN_IN,
    }
    env.update(overrides)
    return env


def test_production_dials_through_twilio():
    app = boot(_production())
    assert isinstance(app.state.call_provider, TwilioCalls)


@pytest.mark.parametrize("missing", ["PUBLIC_BASE_URL", "TWILIO_FROM_NUMBER"])
def test_production_needs_the_call_settings(missing):
    with pytest.raises(RuntimeError, match=missing):
        boot(_production(**{missing: ""}))


def test_production_refuses_to_boot_without_the_prompt_files(tmp_path):
    with pytest.raises(RuntimeError, match="render_prompts"):
        boot(_production(PROMPTS_DIR=str(tmp_path)))


def test_dev_without_twilio_only_records_and_has_no_voice_routes():
    app = boot(
        {
            "ENV": "development",
            "DEV_AUTH": "1",
            "DATABASE_URL": "postgresql://example",
            "CODE_PEPPER": "p",
            "OTP_DERIVATION_KEY": "k",
        }
    )
    assert isinstance(app.state.call_provider, RecordingCallProvider)
    paths = {getattr(route, "path", "") for route in app.routes}
    assert not any(path.startswith("/voice/") for path in paths)


# --- The call against the API ---


@pytest.fixture
def world(database_url):
    clock = ManualClock(NOW)
    http = FakeTwilioHttp()
    voice = Voice(BASE)
    issued = {"n": 0}
    prompts = Path(_fake_prompts())

    def tokens():
        issued["n"] += 1
        return f"session-secret-{issued['n']:04d}-" + ("z" * 24)

    def build(post=http):
        return TestClient(
            create_app(
                connect=lambda: _connect(database_url),
                clock=clock.now,
                rng=lambda n: b"\x42" * n,
                tokens=tokens,
                call_provider=TwilioCalls(
                    account_sid="AC1",
                    auth_token=TOKEN,
                    from_number="+14155550100",
                    voice=voice,
                    post=post,
                ),
                dev_auth=True,
                voice=voice,
                twilio_auth_token=TOKEN,
                prompts_dir=prompts,
            )
        )

    connection = _connect(database_url)
    try:
        yield {
            "client": build(),
            "build": build,
            "clock": clock,
            "http": http,
            "conn": connection,
        }
    finally:
        connection.rollback()
        _wipe(connection)
        connection.close()


def hook(client, kind, case_id, *, sign=True, signed_case=None, token=TOKEN, **params):
    signed = case_id if signed_case is None else signed_case
    url = f"{BASE}/voice/twilio/{kind}?case_id={signed}"
    headers = {}
    if sign:
        headers["X-Twilio-Signature"] = twilio_signature(token, url, params)
    return client.post(f"/voice/twilio/{kind}?case_id={case_id}", data=params, headers=headers)


def app_child(w, country="+1", settle=True):
    """An app-linked child (session and static code), and an open case that is calling."""
    client, clock = w["client"], w["clock"]
    parent = login(client, "Parent")
    child = login(client, "Minji", locale="ko", subject="child-kr" if country == "+82" else "child-us")
    family_id = _family(client, parent["token"])
    member_id = _child(client, parent["token"], family_id)
    phone = next_phone(country)
    assert _activate(client, parent["token"], member_id, phone, child["user_id"]).status_code == 201
    coded = client.post(
        "/v1/me/check-code",
        headers=auth(child["token"]),
        json={"code": "2468", "biometric_ok": False},
    )
    assert coded.status_code == 200
    if settle:
        clock.advance(timedelta(hours=24))
    opened = client.post(
        "/v1/cases",
        headers=auth(parent["token"]),
        json={"child_member_id": member_id, "text": "please send money"},
    )
    assert opened.status_code == 201, opened.text
    case = opened.json()
    return parent, child, case["id"], phone, w["http"].sid()


def call_only_child(w):
    client, clock = w["client"], w["clock"]
    parent = login(client, "Parent")
    family_id = _family(client, parent["token"])
    member_id = _child(client, parent["token"], family_id)
    phone = next_phone()
    assert _activate(client, parent["token"], member_id, phone).status_code == 201
    assert _set_dev_code(client, parent["token"], member_id, "1357").status_code == 200
    clock.advance(timedelta(hours=24))
    opened = client.post(
        "/v1/cases",
        headers=auth(parent["token"]),
        json={"child_member_id": member_id, "text": "please send money"},
    )
    assert opened.status_code == 201, opened.text
    return parent, opened.json()["id"], phone, w["http"].sid()


def case_of(w, token, case_id):
    response = w["client"].get(f"/v1/cases/{case_id}", headers=auth(token))
    assert response.status_code == 200
    return response.json()


def gather_of(response):
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    return parse(response.text)


def the_code(w, child, case_id):
    response = w["client"].get(f"/v1/cases/{case_id}/call-code", headers=auth(child["token"]))
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    return response.json()["code"]


def test_opening_a_case_places_the_call_and_stores_the_sid(world):
    _parent, _child_user, case_id, phone, sid = app_child(world)
    url, kwargs = world["http"].requests[-1]
    assert kwargs["data"]["To"] == phone
    assert kwargs["data"]["Record"] == "false"
    attempts = world["conn"].execute(
        "SELECT status, provider_ref FROM verification_attempts WHERE case_id = %s",
        (case_id,),
    ).fetchall()
    assert attempts == [("sent", sid)]


def test_app_child_one_time_code_then_one_is_green(world):
    client = world["client"]
    parent, child, case_id, _phone, sid = app_child(world)
    greeting = gather_of(hook(client, "outbound", case_id, CallSid=sid)).find("Gather")
    assert greeting.attrib["numDigits"] == "6"
    assert greeting.attrib["finishOnKey"] == "*"
    assert greeting.find("Play").text.endswith("/en/one_time_greeting.mp3")
    code = the_code(world, child, case_id)
    assert re.fullmatch(r"[0-9]{6}", code)
    question = gather_of(hook(client, "code", case_id, CallSid=sid, Digits=code))
    assert question.find("Gather").attrib["numDigits"] == "1"
    assert question.find("Gather/Play").text.endswith("/en/question.mp3")
    thanks = gather_of(hook(client, "answer", case_id, CallSid=sid, Digits="1"))
    assert [c.tag for c in thanks] == ["Play", "Hangup"]
    assert thanks.find("Play").text.endswith("/en/thanks.mp3")
    body = case_of(world, parent["token"], case_id)
    assert (body["state"], body["result"], body["answered_via"]) == ("confirmed", "sent", "call")
    assert code not in str(body)


def test_star_switches_to_the_static_code_then_two_is_red(world):
    client = world["client"]
    parent, _child_user, case_id, _phone, sid = app_child(world, country="+82")
    hook(client, "outbound", case_id, CallSid=sid)
    switched = gather_of(hook(client, "code", case_id, CallSid=sid, Digits=""))
    gather = switched.find("Gather")
    assert gather.attrib["numDigits"] == "4"
    assert gather.attrib["finishOnKey"] == ""
    assert gather.find("Play").text.endswith("/ko/static_switch.mp3")
    assert case_of(world, parent["token"], case_id)["code_channel"] == "static"
    question = gather_of(hook(client, "code", case_id, CallSid=sid, Digits="2468"))
    assert question.find("Gather/Play").text.endswith("/ko/question.mp3")
    hook(client, "answer", case_id, CallSid=sid, Digits="2")
    body = case_of(world, parent["token"], case_id)
    assert (body["state"], body["result"], body["color"]) == ("scam", "not_sent", "red")


def test_a_call_only_child_gets_the_static_greeting(world):
    client = world["client"]
    parent, case_id, _phone, sid = call_only_child(world)
    root = gather_of(hook(client, "outbound", case_id, CallSid=sid))
    gather = root.find("Gather")
    assert gather.attrib["numDigits"] == "4"
    assert gather.find("Play").text.endswith("/en/static_greeting.mp3")
    hook(client, "code", case_id, CallSid=sid, Digits="1357")
    hook(client, "answer", case_id, CallSid=sid, Digits="1")
    assert case_of(world, parent["token"], case_id)["color"] == "green"


def test_one_wrong_code_plays_code_failed_and_hangs_up(world):
    client = world["client"]
    parent, case_id, _phone, sid = call_only_child(world)
    root = gather_of(hook(client, "code", case_id, CallSid=sid, Digits="9999"))
    assert [c.tag for c in root] == ["Play", "Hangup"]
    assert root.find("Play").text.endswith("/en/code_failed.mp3")
    body = case_of(world, parent["token"], case_id)
    assert (body["state"], body["result"]) == ("not_confirmed", "wrong")
    again = gather_of(hook(client, "code", case_id, CallSid=sid, Digits="1357"))
    assert [c.tag for c in again] == ["Hangup"]
    assert case_of(world, parent["token"], case_id)["result"] == "wrong"


def test_a_wrong_one_time_code_does_not_offer_the_static_code(world):
    client = world["client"]
    parent, child, case_id, _phone, sid = app_child(world)
    code = the_code(world, child, case_id)
    wrong = f"{(int(code) + 1) % 1_000_000:06d}"
    root = gather_of(hook(client, "code", case_id, CallSid=sid, Digits=wrong))
    assert root.find("Gather") is None
    assert root.find("Play").text.endswith("/code_failed.mp3")
    assert case_of(world, parent["token"], case_id)["result"] == "wrong"


def test_an_unsigned_or_badly_signed_webhook_is_403(world):
    client = world["client"]
    parent, case_id, _phone, sid = call_only_child(world)
    unsigned = hook(client, "code", case_id, sign=False, CallSid=sid, Digits="1357")
    assert unsigned.status_code == 403
    wrong_token = hook(client, "code", case_id, token="nope", CallSid=sid, Digits="1357")
    assert wrong_token.status_code == 403
    other_case = hook(
        client, "code", case_id, signed_case="00000000-0000-4000-8000-000000000000",
        CallSid=sid, Digits="1357",
    )
    assert other_case.status_code == 403
    tampered = client.post(
        f"/voice/twilio/status?case_id={case_id}",
        data={"CallSid": sid, "CallStatus": "completed"},
        headers={"X-Twilio-Signature": twilio_signature(
            TOKEN, f"{BASE}/voice/twilio/status?case_id={case_id}",
            {"CallSid": sid, "CallStatus": "no-answer"},
        )},
    )
    assert tampered.status_code == 403
    assert case_of(world, parent["token"], case_id)["state"] == "calling"


def test_a_different_call_sid_changes_nothing(world):
    client = world["client"]
    parent, case_id, _phone, _sid = call_only_child(world)
    root = gather_of(hook(client, "code", case_id, CallSid="CA" + "f" * 32, Digits="9999"))
    assert [c.tag for c in root] == ["Hangup"]
    hook(client, "status", case_id, CallSid="CA" + "f" * 32, CallStatus="no-answer")
    assert case_of(world, parent["token"], case_id)["state"] == "calling"


@pytest.mark.parametrize("status", ["no-answer", "busy"])
def test_nobody_answering_is_yellow_timeout_never_not_sent(world, status):
    client = world["client"]
    parent, case_id, _phone, sid = call_only_child(world)
    hook(client, "status", case_id, CallSid=sid, CallStatus=status)
    body = case_of(world, parent["token"], case_id)
    assert (body["state"], body["result"], body["color"]) == ("not_confirmed", "timeout", "yellow")
    assert f"call_{status.replace('-', '_')}" in body["timeline"]
    attempt = world["conn"].execute(
        "SELECT status, ended_at FROM verification_attempts WHERE case_id = %s", (case_id,)
    ).fetchone()
    assert attempt[0] == "failed" and attempt[1] is not None


def test_a_failed_call_is_call_failed(world):
    client = world["client"]
    parent, case_id, _phone, sid = call_only_child(world)
    hook(client, "status", case_id, CallSid=sid, CallStatus="failed")
    assert case_of(world, parent["token"], case_id)["result"] == "call_failed"


def test_hanging_up_mid_call_is_yellow(world):
    client = world["client"]
    parent, case_id, _phone, sid = call_only_child(world)
    hook(client, "code", case_id, CallSid=sid, Digits="1357")
    hook(client, "status", case_id, CallSid=sid, CallStatus="completed")
    body = case_of(world, parent["token"], case_id)
    assert (body["result"], body["color"]) == ("no_answer", "yellow")
    other_parent, other_case, _p, other_sid = call_only_child(world)
    hook(client, "status", other_case, CallSid=other_sid, CallStatus="completed")
    assert case_of(world, other_parent["token"], other_case)["result"] == "timeout"


def test_a_status_after_the_answer_changes_nothing(world):
    client = world["client"]
    parent, case_id, _phone, sid = call_only_child(world)
    hook(client, "code", case_id, CallSid=sid, Digits="1357")
    hook(client, "answer", case_id, CallSid=sid, Digits="2")
    hook(client, "status", case_id, CallSid=sid, CallStatus="no-answer")
    assert case_of(world, parent["token"], case_id)["result"] == "not_sent"


@pytest.mark.parametrize("digits", ["5", "", "0", "#"])
def test_anything_but_one_or_two_after_the_code_is_no_answer(world, digits):
    client = world["client"]
    parent, case_id, _phone, sid = call_only_child(world)
    hook(client, "code", case_id, CallSid=sid, Digits="1357")
    root = gather_of(hook(client, "answer", case_id, CallSid=sid, Digits=digits))
    assert root.find("Play").text.endswith("/thanks.mp3")
    body = case_of(world, parent["token"], case_id)
    assert (body["result"], body["color"]) == ("no_answer", "yellow")


def test_one_digit_before_the_code_replays_the_gather(world):
    client = world["client"]
    parent, case_id, _phone, sid = call_only_child(world)
    replay = gather_of(hook(client, "code", case_id, CallSid=sid, Digits="1"))
    assert replay.find("Gather").attrib["numDigits"] == "4"
    early_answer = gather_of(hook(client, "answer", case_id, CallSid=sid, Digits="1"))
    assert early_answer.find("Gather").attrib["action"].endswith(f"/code?case_id={case_id}")
    body = case_of(world, parent["token"], case_id)
    assert (body["state"], body["result"]) == ("calling", None)


def test_silence_on_the_static_gather_hangs_up_without_a_verdict(world):
    client = world["client"]
    parent, case_id, _phone, sid = call_only_child(world)
    root = gather_of(hook(client, "code", case_id, CallSid=sid, Digits=""))
    assert [c.tag for c in root] == ["Hangup"]
    assert case_of(world, parent["token"], case_id)["state"] == "calling"


def test_a_push_answer_during_the_call_wins_and_the_call_hangs_up(world):
    client = world["client"]
    parent, child, case_id, _phone, sid = app_child(world)
    code = the_code(world, child, case_id)
    answered = client.post(
        f"/v1/cases/{case_id}/answer", headers=auth(child["token"]), json={"answer": "no"}
    )
    assert answered.json()["color"] == "red"
    for kind, digits in (("outbound", None), ("code", code)):
        params = {"CallSid": sid}
        if digits is not None:
            params["Digits"] = digits
        root = gather_of(hook(client, kind, case_id, **params))
        assert [c.tag for c in root] == ["Hangup"]
    assert case_of(world, parent["token"], case_id)["result"] == "not_sent"


def test_a_yes_on_a_new_number_stays_yellow(world):
    client = world["client"]
    parent, child, case_id, _phone, sid = app_child(world, settle=False)
    hook(client, "code", case_id, CallSid=sid, Digits=the_code(world, child, case_id))
    hook(client, "answer", case_id, CallSid=sid, Digits="1")
    assert case_of(world, parent["token"], case_id)["result"] == "number_recent"


# --- The call-code route ---


def test_call_code_is_child_only(world):
    client, clock = world["client"], world["clock"]
    parent, child, case_id, _phone, _sid = app_child(world)
    denied = client.get(f"/v1/cases/{case_id}/call-code", headers=auth(parent["token"]))
    assert denied.status_code == 403
    assert denied.json() == {"error": "not_the_child"}
    stranger = login(client, "Stranger", subject="stranger")
    hidden = client.get(f"/v1/cases/{case_id}/call-code", headers=auth(stranger["token"]))
    assert hidden.status_code == 404
    assert the_code(world, child, case_id)
    clock.advance(timedelta(minutes=5))
    expired = client.get(f"/v1/cases/{case_id}/call-code", headers=auth(child["token"]))
    assert expired.json() == {"code": None, "fallback": "static"}


def test_a_second_process_with_the_same_key_shows_the_same_code(world):
    _parent, child, case_id, _phone, _sid = app_child(world)
    first = the_code(world, child, case_id)
    other = world["build"]()
    second = other.get(f"/v1/cases/{case_id}/call-code", headers=auth(child["token"]))
    assert second.json() == {"code": first}


def test_a_used_code_is_not_shown_again(world):
    client = world["client"]
    _parent, child, case_id, _phone, sid = app_child(world)
    code = the_code(world, child, case_id)
    hook(client, "code", case_id, CallSid=sid, Digits=code)
    response = client.get(f"/v1/cases/{case_id}/call-code", headers=auth(child["token"]))
    assert response.json() == {"code": None, "fallback": "static"}


# --- Dialing, prompts, and logs ---


def test_a_refused_call_is_yellow_call_failed(world):
    refusing = FakeTwilioHttp(status=500)
    client = world["build"](post=refusing)
    parent = login(client, "Parent")
    family_id = _family(client, parent["token"])
    member_id = _child(client, parent["token"], family_id)
    assert _activate(client, parent["token"], member_id, next_phone()).status_code == 201
    assert _set_dev_code(client, parent["token"], member_id, "1357").status_code == 200
    opened = client.post(
        "/v1/cases",
        headers=auth(parent["token"]),
        json={"child_member_id": member_id, "text": "money"},
    )
    assert opened.status_code == 201
    body = opened.json()
    assert (body["state"], body["result"], body["color"]) == ("not_confirmed", "call_failed", "yellow")
    attempt = world["conn"].execute(
        "SELECT status, provider_ref FROM verification_attempts WHERE case_id = %s",
        (UUID(body["id"]),),
    ).fetchone()
    assert attempt == ("failed", None)


def test_prompts_are_served_by_name_only(world):
    client = world["client"]
    ok = client.get("/voice/prompts/ko/question.mp3")
    assert ok.status_code == 200
    assert ok.headers["content-type"] == "audio/mpeg"
    for bad in ("/voice/prompts/fr/question.mp3", "/voice/prompts/en/secret.mp3",
                "/voice/prompts/en/..%2F..%2Fschema.mp3"):
        assert client.get(bad).status_code == 404


def test_digits_never_reach_the_log(world, caplog):
    client = world["client"]
    caplog.set_level(logging.DEBUG)
    _parent, case_id, _phone, sid = call_only_child(world)
    hook(client, "code", case_id, CallSid=sid, Digits="1357")
    hook(client, "answer", case_id, CallSid=sid, Digits="2")
    assert "1357" not in caplog.text
