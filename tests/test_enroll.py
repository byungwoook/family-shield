"""Milestone 5: sign-in, invites, SMS OTP for +1 and +82, and parent confirm.

Readings, where the milestone text allows more than one:

- Sign-in returns 200 with a session token. The same provider and subject
  is the same user. A bad token is 401 `invalid_token` and writes nothing.
- An invite secret is 12 characters from `INVITE_ALPHABET`, shown as
  `XXXX-XXXX-XXXX`, and is returned only by the add-child and re-issue
  responses. Case and dashes do not matter on accept. An expired secret is
  `invite_expired`. A used, replaced, or unknown secret is `invite_invalid`.
  A parent can re-issue an invite while no child account has accepted it.
- OTP: 10 minutes, 5 tries. The fifth miss kills the challenge and the
  right code after it is `otp_expired`. A new challenge replaces the older
  live one. At most 5 challenges per member in 24 hours, then
  `rate_limited` with no SMS. Whether a number is already enrolled is only
  revealed after the OTP succeeds.
- Confirm needs an accepted invite and a verified number. Before confirm
  the child is not callable and `POST /v1/cases` is `member_not_callable`.
  After confirm it is 201. (The milestone says 200; this API answers a
  created case with 201, as in milestone 4.)
- The SMS goes out after the commit. If the sender fails, the response is
  502 `sms_failed` and the challenge still counts toward the cap.
"""

import logging
from datetime import timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from backend.api import boot, create_app
from backend.codes import hash_one_time
from backend.enroll import (
    INVITE_ALPHABET,
    INVITE_LEN,
    DevOtp,
    OtpSendFailed,
    TwilioOtp,
    format_invite,
    hash_invite,
    hash_otp,
    new_invite_secret,
    new_otp_code,
    normalize_invite,
    otp_matches,
    otp_message,
)
from backend.signin import apple_verifier, google_verifier
from test_api import (  # noqa: F401  (database_url and secrets are fixtures)
    NOW,
    PRODUCTION_SIGN_IN,
    ManualClock,
    RecordingCallProvider,
    _connect,
    _wipe,
    auth,
    database_url,
    login,
    next_phone,
    secrets,
)


APPLE_AUD = "com.example.familyshield"
GOOGLE_AUD = "1234-server.apps.googleusercontent.com"
SIGNING_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def lookup(kid):
    return {"k1": SIGNING_KEY.public_key()}[kid]


def id_token(provider, sub, clock, aud=None):
    if provider == "apple":
        iss, default_aud = "https://appleid.apple.com", APPLE_AUD
    else:
        iss, default_aud = "https://accounts.google.com", GOOGLE_AUD
    now = clock.now()
    claims = {
        "iss": iss,
        "aud": default_aud if aud is None else aud,
        "sub": sub,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
    }
    return jwt.encode(claims, SIGNING_KEY, algorithm="RS256", headers={"kid": "k1"})


class FailingOtp:
    def __init__(self):
        self.tries = 0

    def send(self, phone_e164, code):
        self.tries += 1
        raise OtpSendFailed("twilio status 500")


@pytest.fixture
def env(database_url):
    clock = ManualClock(NOW)
    calls = RecordingCallProvider()
    sms = DevOtp()
    issued = {"n": 0}

    def tokens():
        issued["n"] += 1
        return f"session-secret-{issued['n']:04d}-" + ("y" * 24)

    def build(otp_sender=sms):
        return TestClient(
            create_app(
                connect=lambda: _connect(database_url),
                clock=clock.now,
                rng=lambda n: b"\x42" * n,
                tokens=tokens,
                call_provider=calls,
                dev_auth=True,
                verifiers={
                    "apple": apple_verifier(APPLE_AUD, keys=lookup),
                    "google": google_verifier(GOOGLE_AUD, keys=lookup),
                },
                otp_sender=otp_sender,
            )
        )

    connection = _connect(database_url)
    state = {
        "client": build(),
        "build": build,
        "clock": clock,
        "calls": calls,
        "sms": sms,
        "conn": connection,
    }
    try:
        yield state
    finally:
        connection.rollback()
        _wipe(connection)
        connection.close()


# --- helpers ---


def sign_in(client, clock, provider, sub, locale="en", name=None):
    body = {"id_token": id_token(provider, sub, clock), "locale": locale}
    if name is not None:
        body["display_name"] = name
    response = client.post(f"/v1/auth/{provider}", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def new_family(client, token):
    response = client.post("/v1/families", headers=auth(token), json={"name": "Kim"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def invite_child(client, token, family_id, name="민지"):
    response = client.post(
        f"/v1/families/{family_id}/children",
        headers=auth(token),
        json={"display_name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def accept(client, token, secret):
    return client.post("/v1/invites/accept", headers=auth(token), json={"secret": secret})


def start_otp(client, token, phone):
    return client.post("/v1/phones/otp", headers=auth(token), json={"phone_e164": phone})


def check_otp(client, token, phone, code):
    return client.post(
        "/v1/phones/otp/check",
        headers=auth(token),
        json={"phone_e164": phone, "code": code},
    )


def decide(client, token, family_id, member_id, decision):
    return client.post(
        f"/v1/families/{family_id}/members/{member_id}/confirm",
        headers=auth(token),
        json={"decision": decision},
    )


def open_case(client, token, member_id):
    return client.post(
        "/v1/cases",
        headers=auth(token),
        json={"child_member_id": member_id, "text": "please send money"},
    )


def wrong_code(code):
    return f"{(int(code) + 1) % 1_000_000:06d}"


def enrolled(env, *, country="+1", confirm=True):
    """Parent (Apple) and child (Google) through invite and OTP."""
    client, clock = env["client"], env["clock"]
    parent = sign_in(client, clock, "apple", "parent-sub", name="Mom")
    child = sign_in(client, clock, "google", "child-sub", locale="ko", name="Minji")
    family_id = new_family(client, parent["token"])
    invite = invite_child(client, parent["token"], family_id)
    accepted = accept(client, child["token"], invite["invite_secret"])
    assert accepted.status_code == 200, accepted.text
    phone = next_phone(country)
    started = start_otp(client, child["token"], phone)
    assert started.status_code == 202, started.text
    sent_phone, code = env["sms"].sent[-1]
    assert sent_phone == phone
    checked = check_otp(client, child["token"], phone, code)
    assert checked.status_code == 200, checked.text
    if confirm:
        confirmed = decide(client, parent["token"], family_id, invite["id"], "confirm")
        assert confirmed.status_code == 200, confirmed.text
    return parent, child, family_id, invite["id"], phone


def invited(env):
    client, clock = env["client"], env["clock"]
    parent = sign_in(client, clock, "apple", "parent-sub")
    child = sign_in(client, clock, "google", "child-sub")
    family_id = new_family(client, parent["token"])
    invite = invite_child(client, parent["token"], family_id)
    assert accept(client, child["token"], invite["invite_secret"]).status_code == 200
    return parent, child, family_id, invite["id"]


def count(conn, sql, params=()):
    conn.rollback()
    return conn.execute(sql, params).fetchone()[0]


# --- Pure: invite secrets and OTP codes ---


def test_invite_secret_shape_and_alphabet():
    secret = new_invite_secret()
    assert len(secret) == INVITE_LEN == 12
    assert set(secret) <= set(INVITE_ALPHABET)
    assert not set("01OIL") & set(INVITE_ALPHABET)
    assert len(INVITE_ALPHABET) == 31
    assert format_invite(secret).count("-") == 2


def test_invite_rng_discards_the_biased_tail():
    chunks = iter([bytes([255] * 32), bytes([0, 30, 31, 247] * 8)])
    secret = new_invite_secret(lambda n: next(chunks))
    assert secret == ("2Z2Z" * 3)


def test_normalize_invite_folds_case_and_separators_only():
    secret = new_invite_secret()
    pretty = format_invite(secret)
    assert normalize_invite(pretty) == secret
    assert normalize_invite(pretty.lower().replace("-", " ")) == secret
    for bad in ("", "ABC", secret + "2", secret[:-1] + "0", secret[:-1] + "O", None, 12):
        assert normalize_invite(bad) is None


def test_invite_hash_is_keyed_and_not_the_secret(monkeypatch):
    secret = new_invite_secret()
    digest = hash_invite(secret)
    assert len(digest) == 64 and secret not in digest
    monkeypatch.setenv("CODE_PEPPER", "another-pepper-0123456789")
    assert hash_invite(secret) != digest


def test_otp_code_is_six_uniform_digits():
    draws = iter([b"\xff\xff\xff\xff", (123_456).to_bytes(4, "big")])
    assert new_otp_code(lambda n: next(draws)) == "123456"
    assert len(new_otp_code()) == 6 and new_otp_code().isdigit()


def test_otp_hash_is_bound_to_the_number_and_apart_from_call_codes():
    us, kr = "+14155550123", "+821012345678"
    assert hash_otp(us, "123456") != hash_otp(kr, "123456")
    assert hash_otp(us, "123456") != hash_one_time("123456")
    assert otp_matches(us, "123456", hash_otp(us, "123456"))
    assert not otp_matches(kr, "123456", hash_otp(us, "123456"))
    for bad in ("12345", "1234567", "12345a", "", None, 123456):
        assert not otp_matches(us, bad, hash_otp(us, "123456"))


def test_sms_language_follows_the_number_and_says_it_is_not_the_check_code():
    korean = otp_message("+821012345678", "482910")
    english = otp_message("+14155550123", "482910")
    assert "인증번호" in korean and "확인 번호" in korean
    assert "not your check code" in english
    assert korean.count("482910") == english.count("482910") == 1


def test_twilio_sender_posts_one_message_and_hides_the_code_on_failure():
    posts = []

    class Response:
        def __init__(self, status):
            self.status_code = status

    def post(url, **kwargs):
        posts.append((url, kwargs))
        return Response(201 if len(posts) == 1 else 400)

    sender = TwilioOtp(
        account_sid="AC123", auth_token="tok", from_number="+14155550100", post=post
    )
    sender.send("+821012345678", "482910")
    url, kwargs = posts[0]
    assert url == "https://api.twilio.com/2010-04-01/Accounts/AC123/Messages.json"
    assert kwargs["data"]["To"] == "+821012345678"
    assert kwargs["data"]["From"] == "+14155550100"
    assert "482910" in kwargs["data"]["Body"]
    assert kwargs["auth"] == ("AC123", "tok")
    assert kwargs["timeout"] == 10
    with pytest.raises(OtpSendFailed) as caught:
        sender.send("+14155550123", "777111")
    assert "777111" not in str(caught.value)


def test_twilio_sender_can_use_a_messaging_service():
    posts = []

    class Ok:
        status_code = 201

    sender = TwilioOtp(
        account_sid="AC1",
        auth_token="t",
        messaging_service_sid="MG1",
        post=lambda url, **kw: posts.append(kw) or Ok(),
    )
    sender.send("+14155550123", "000111")
    assert posts[0]["data"]["MessagingServiceSid"] == "MG1"
    assert "From" not in posts[0]["data"]


@pytest.mark.parametrize(
    "missing", ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"]
)
def test_twilio_settings_are_required_outside_dev(missing):
    env = {
        "ENV": "production",
        "DATABASE_URL": "postgresql://example",
        "CODE_PEPPER": "p",
        "OTP_DERIVATION_KEY": "k",
        **PRODUCTION_SIGN_IN,
    }
    env[missing] = ""
    with pytest.raises(RuntimeError, match="TWILIO_"):
        boot(env)


@pytest.mark.parametrize("missing", ["APPLE_BUNDLE_ID", "GOOGLE_SERVER_CLIENT_ID"])
def test_sign_in_audiences_are_required_outside_dev(missing):
    env = {
        "ENV": "production",
        "DATABASE_URL": "postgresql://example",
        "CODE_PEPPER": "p",
        "OTP_DERIVATION_KEY": "k",
        **PRODUCTION_SIGN_IN,
    }
    env[missing] = " "
    with pytest.raises(RuntimeError, match=missing):
        boot(env)


def test_dev_otp_is_never_the_production_sender():
    base = {
        "DATABASE_URL": "postgresql://example",
        "CODE_PEPPER": "p",
        "OTP_DERIVATION_KEY": "k",
    }
    production = boot({**base, "ENV": "production", **PRODUCTION_SIGN_IN})
    assert isinstance(production.state.otp_sender, TwilioOtp)
    development = boot({**base, "ENV": "development", "DEV_AUTH": "1", **PRODUCTION_SIGN_IN})
    assert isinstance(development.state.otp_sender, DevOtp)
    paths = {getattr(route, "path", "") for route in production.routes}
    for path in (
        "/v1/auth/apple",
        "/v1/auth/google",
        "/v1/invites/accept",
        "/v1/phones/otp",
        "/v1/phones/otp/check",
        "/v1/families/{family_id}/members/{member_id}/confirm",
    ):
        assert path in paths


def test_a_blank_audience_in_dev_answers_sign_in_unavailable():
    app = boot(
        {
            "ENV": "development",
            "DEV_AUTH": "1",
            "DATABASE_URL": "postgresql://example",
            "CODE_PEPPER": "p",
            "OTP_DERIVATION_KEY": "k",
        }
    )
    client = TestClient(app)
    for provider in ("apple", "google"):
        response = client.post(
            f"/v1/auth/{provider}", json={"id_token": "x.y.z", "locale": "en"}
        )
        assert response.status_code == 503
        assert response.json() == {"error": "sign_in_unavailable"}


# --- Sign-in against the API ---


def test_sign_in_is_an_upsert_on_provider_and_subject(env):
    client, clock, conn = env["client"], env["clock"], env["conn"]
    first = sign_in(client, clock, "apple", "same-sub", name="Mom")
    second = sign_in(client, clock, "apple", "same-sub", name="Someone else")
    google = sign_in(client, clock, "google", "same-sub")
    assert first["user_id"] == second["user_id"] != google["user_id"]
    assert first["token"] != second["token"]
    assert count(conn, "SELECT count(*) FROM users") == 2
    name = conn.execute(
        "SELECT display_name FROM users WHERE id = %s", (first["user_id"],)
    ).fetchone()[0]
    assert name == "Mom"
    me = client.post("/v1/families", headers=auth(second["token"]), json={"name": "Kim"})
    assert me.status_code == 201


def test_a_bad_id_token_is_401_and_writes_nothing(env):
    client, clock, conn = env["client"], env["clock"], env["conn"]
    wrong_aud = id_token("apple", "s", clock, aud="com.example.other")
    google_for_apple = id_token("google", "s", clock)
    for token in (wrong_aud, google_for_apple, "not-a-token"):
        response = client.post("/v1/auth/apple", json={"id_token": token, "locale": "en"})
        assert response.status_code == 401
        assert response.json() == {"error": "invalid_token"}
    clock.advance(timedelta(minutes=20))
    stale = id_token("apple", "s", ManualClock(NOW))
    response = client.post("/v1/auth/apple", json={"id_token": stale, "locale": "en"})
    assert response.status_code == 401
    assert count(conn, "SELECT count(*) FROM users") == 0
    assert count(conn, "SELECT count(*) FROM sessions") == 0


def test_sign_in_refuses_an_unknown_locale_and_extra_fields(env):
    client, clock = env["client"], env["clock"]
    token = id_token("apple", "s", clock)
    bad_locale = client.post("/v1/auth/apple", json={"id_token": token, "locale": "fr"})
    assert bad_locale.status_code == 400
    extra = client.post(
        "/v1/auth/apple", json={"id_token": token, "locale": "en", "email": "a@b.c"}
    )
    assert extra.status_code == 400
    assert extra.json() == {"error": "invalid_body"}


# --- The enrollment loop ---


def test_full_enrollment_then_confirm_makes_the_child_callable(env):
    client, conn, calls = env["client"], env["conn"], env["calls"]
    parent, child, family_id, member_id, phone = enrolled(env, country="+82", confirm=False)

    roster = client.get(f"/v1/families/{family_id}/members", headers=auth(parent["token"]))
    assert roster.status_code == 200
    kid = next(m for m in roster.json()["members"] if m["id"] == member_id)
    assert kid["awaiting_confirm"] is True
    assert kid["phone_last4"] == phone[-4:]
    assert kid["linked"] is True and kid["phone_verified"] is True
    assert phone not in roster.text
    assert "invite_hash" not in roster.text

    before = open_case(client, parent["token"], member_id)
    assert before.status_code == 400
    assert before.json() == {"error": "member_not_callable"}
    assert calls.calls == []

    confirmed = decide(client, parent["token"], family_id, member_id, "confirm")
    assert confirmed.status_code == 200
    assert confirmed.json() == {"id": member_id, "status": "active", "phone_last4": phone[-4:]}

    denied = open_case(client, child["token"], member_id)
    assert denied.status_code == 403
    assert denied.json() == {"error": "not_a_parent"}

    opened = open_case(client, parent["token"], member_id)
    assert opened.status_code == 201, opened.text
    case = opened.json()
    assert case["state"] == "calling"
    assert case["code_channel"] == "one_time"
    assert calls.calls == [f"would call {phone}"]

    parent_answer = client.post(
        f"/v1/cases/{case['id']}/answer",
        headers=auth(parent["token"]),
        json={"answer": "no"},
    )
    assert parent_answer.status_code == 403
    assert parent_answer.json() == {"error": "not_the_child"}
    child_answer = client.post(
        f"/v1/cases/{case['id']}/answer",
        headers=auth(child["token"]),
        json={"answer": "no"},
    )
    assert child_answer.status_code == 200
    assert child_answer.json()["color"] == "red"

    steps = [
        row[0]
        for row in conn.execute(
            "SELECT step FROM family_events WHERE family_id = %s ORDER BY seq",
            (family_id,),
        ).fetchall()
    ]
    assert set(steps) == {"child_invited", "invite_accepted", "phone_verified", "child_confirmed"}


def test_a_korean_number_is_accepted_and_a_uk_number_is_not(env):
    client, conn, sms = env["client"], env["conn"], env["sms"]
    _parent, child, _family_id, _member_id = invited(env)
    uk = start_otp(client, child["token"], "+442079460958")
    assert uk.status_code == 400
    assert uk.json() == {"error": "unsupported_country"}
    assert sms.sent == []
    assert count(conn, "SELECT count(*) FROM phone_otp") == 0
    korean = next_phone("+82")
    response = start_otp(client, child["token"], korean)
    assert response.status_code == 202
    assert response.json()["phone_last4"] == korean[-4:]
    assert sms.sent[-1][0] == korean
    assert sms.sent[-1][1] not in response.text


def test_the_dev_sender_writes_the_code_to_the_log(env, caplog):
    client = env["client"]
    _parent, child, _family_id, _member_id = invited(env)
    caplog.set_level(logging.INFO, logger="backend.enroll")
    phone = next_phone()
    assert start_otp(client, child["token"], phone).status_code == 202
    code = env["sms"].sent[-1][1]
    assert code in caplog.text
    assert phone not in caplog.text


# --- Invites ---


def test_an_expired_invite_is_refused_and_a_reissued_one_works(env):
    client, clock, conn = env["client"], env["clock"], env["conn"]
    parent = sign_in(client, clock, "apple", "parent-sub")
    child = sign_in(client, clock, "google", "child-sub")
    family_id = new_family(client, parent["token"])
    invite = invite_child(client, parent["token"], family_id)
    clock.advance(timedelta(hours=24))
    expired = accept(client, child["token"], invite["invite_secret"])
    assert expired.status_code == 400
    assert expired.json() == {"error": "invite_expired"}
    assert count(
        conn, "SELECT count(*) FROM family_members WHERE user_id = %s", (child["user_id"],)
    ) == 0

    again = client.post(
        f"/v1/families/{family_id}/members/{invite['id']}/invite",
        headers=auth(parent["token"]),
    )
    assert again.status_code == 201
    fresh = again.json()["invite_secret"]
    assert fresh != invite["invite_secret"]
    old = accept(client, child["token"], invite["invite_secret"])
    assert old.json() == {"error": "invite_invalid"}
    ok = accept(client, child["token"], fresh.lower().replace("-", " "))
    assert ok.status_code == 200
    assert ok.json()["member_id"] == invite["id"]


def test_a_used_invite_cannot_be_used_again(env):
    client, clock, conn = env["client"], env["clock"], env["conn"]
    parent = sign_in(client, clock, "apple", "parent-sub")
    child = sign_in(client, clock, "google", "child-sub")
    thief = sign_in(client, clock, "google", "thief-sub")
    family_id = new_family(client, parent["token"])
    invite = invite_child(client, parent["token"], family_id)
    assert accept(client, child["token"], invite["invite_secret"]).status_code == 200
    reused = accept(client, thief["token"], invite["invite_secret"])
    assert reused.status_code == 400
    assert reused.json() == {"error": "invite_invalid"}
    twice = accept(client, child["token"], invite["invite_secret"])
    assert twice.json() == {"error": "invite_invalid"}
    hash_left = conn.execute(
        "SELECT invite_hash FROM family_members WHERE id = %s", (invite["id"],)
    ).fetchone()[0]
    assert hash_left is None
    reissue = client.post(
        f"/v1/families/{family_id}/members/{invite['id']}/invite",
        headers=auth(parent["token"]),
    )
    assert reissue.status_code == 409
    assert reissue.json() == {"error": "invite_not_open"}


@pytest.mark.parametrize("secret", ["", "2580", "ABCD-EFGH-IJKL", "0" * 12, "x" * 64])
def test_garbage_invites_are_invalid(env, secret):
    client, clock = env["client"], env["clock"]
    child = sign_in(client, clock, "google", "child-sub")
    response = accept(client, child["token"], secret)
    assert response.status_code == 400
    assert response.json() == {"error": "invite_invalid"}


def test_a_parent_and_an_already_linked_child_cannot_accept(env):
    client, clock = env["client"], env["clock"]
    parent, child, family_id, _member_id = invited(env)
    second = invite_child(client, parent["token"], family_id, name="Jun")
    as_parent = accept(client, parent["token"], second["invite_secret"])
    assert as_parent.status_code == 409
    assert as_parent.json() == {"error": "already_in_a_family"}
    as_child = accept(client, child["token"], second["invite_secret"])
    assert as_child.status_code == 409
    assert as_child.json() == {"error": "already_in_a_family"}
    other = sign_in(client, clock, "google", "jun-sub")
    assert accept(client, other["token"], second["invite_secret"]).status_code == 200


def test_the_secret_is_shown_once_and_stored_only_as_a_hash(env):
    client, clock, conn = env["client"], env["clock"], env["conn"]
    parent = sign_in(client, clock, "apple", "parent-sub")
    family_id = new_family(client, parent["token"])
    invite = invite_child(client, parent["token"], family_id)
    secret = normalize_invite(invite["invite_secret"])
    stored = conn.execute(
        "SELECT invite_hash FROM family_members WHERE id = %s", (invite["id"],)
    ).fetchone()[0]
    assert stored == hash_invite(secret)
    roster = client.get(f"/v1/families/{family_id}/members", headers=auth(parent["token"]))
    assert secret not in roster.text
    assert invite["invite_secret"] not in roster.text


# --- OTP ---


def test_five_wrong_codes_kill_the_challenge(env):
    client, conn, sms = env["client"], env["conn"], env["sms"]
    _parent, child, _family_id, member_id = invited(env)
    phone = next_phone("+82")
    assert start_otp(client, child["token"], phone).status_code == 202
    code = sms.sent[-1][1]
    for _ in range(5):
        miss = check_otp(client, child["token"], phone, wrong_code(code))
        assert miss.status_code == 400
        assert miss.json() == {"error": "otp_wrong"}
    dead = check_otp(client, child["token"], phone, code)
    assert dead.status_code == 400
    assert dead.json() == {"error": "otp_expired"}
    assert conn.execute(
        "SELECT phone_e164 FROM family_members WHERE id = %s", (member_id,)
    ).fetchone()[0] is None
    assert count(conn, "SELECT max(attempts) FROM phone_otp") == 5

    assert start_otp(client, child["token"], phone).status_code == 202
    retry = check_otp(client, child["token"], phone, sms.sent[-1][1])
    assert retry.status_code == 200
    assert retry.json() == {"status": "verified", "phone_last4": phone[-4:]}


def test_an_otp_expires_after_ten_minutes(env):
    client, clock, sms = env["client"], env["clock"], env["sms"]
    _parent, child, _family_id, _member_id = invited(env)
    phone = next_phone()
    assert start_otp(client, child["token"], phone).status_code == 202
    clock.advance(timedelta(minutes=10))
    late = check_otp(client, child["token"], phone, sms.sent[-1][1])
    assert late.json() == {"error": "otp_expired"}


def test_a_new_challenge_replaces_the_old_one(env):
    client, sms = env["client"], env["sms"]
    _parent, child, _family_id, _member_id = invited(env)
    phone = next_phone()
    assert start_otp(client, child["token"], phone).status_code == 202
    first = sms.sent[-1][1]
    assert start_otp(client, child["token"], phone).status_code == 202
    second = sms.sent[-1][1]
    if first != second:
        assert check_otp(client, child["token"], phone, first).json() == {"error": "otp_wrong"}
    assert check_otp(client, child["token"], phone, second).status_code == 200


def test_the_code_only_matches_the_number_it_was_sent_to(env):
    client, sms = env["client"], env["sms"]
    _parent, child, _family_id, _member_id = invited(env)
    phone = next_phone()
    assert start_otp(client, child["token"], phone).status_code == 202
    other = check_otp(client, child["token"], next_phone(), sms.sent[-1][1])
    assert other.json() == {"error": "otp_expired"}


def test_five_sends_a_day_then_rate_limited(env):
    client, clock, conn, sms = env["client"], env["clock"], env["conn"], env["sms"]
    _parent, child, _family_id, _member_id = invited(env)
    phone = next_phone()
    for _ in range(5):
        assert start_otp(client, child["token"], phone).status_code == 202
        clock.advance(timedelta(minutes=1))
    sixth = start_otp(client, child["token"], phone)
    assert sixth.status_code == 429
    assert sixth.json() == {"error": "rate_limited"}
    assert len(sms.sent) == 5
    assert count(conn, "SELECT count(*) FROM phone_otp") == 5
    clock.advance(timedelta(hours=24))
    assert start_otp(client, child["token"], phone).status_code == 202


def test_a_number_held_by_another_member_is_refused_only_after_the_code(env):
    client, clock, sms = env["client"], env["clock"], env["sms"]
    parent, _child, family_id, _member_id, phone = enrolled(env)
    second = invite_child(client, parent["token"], family_id, name="Jun")
    jun = sign_in(client, clock, "google", "jun-sub")
    assert accept(client, jun["token"], second["invite_secret"]).status_code == 200
    started = start_otp(client, jun["token"], phone)
    assert started.status_code == 202
    taken = check_otp(client, jun["token"], phone, sms.sent[-1][1])
    assert taken.status_code == 409
    assert taken.json() == {"error": "phone_in_use"}


def test_otp_routes_are_child_only(env):
    client, clock = env["client"], env["clock"]
    parent = sign_in(client, clock, "apple", "parent-sub")
    new_family(client, parent["token"])
    stranger = sign_in(client, clock, "google", "nobody")
    for token in (parent["token"], stranger["token"]):
        response = start_otp(client, token, next_phone())
        assert response.status_code == 403
        assert response.json() == {"error": "not_a_child"}
    assert env["sms"].sent == []
    unauth = client.post("/v1/phones/otp", json={"phone_e164": next_phone()})
    assert unauth.status_code == 401


def test_a_confirmed_child_cannot_restart_otp_here(env):
    client = env["client"]
    _parent, child, _family_id, _member_id, _phone = enrolled(env)
    response = start_otp(client, child["token"], next_phone())
    assert response.status_code == 409
    assert response.json() == {"error": "phone_already_set"}


def test_a_failed_sms_is_502_and_still_counts(env):
    failing = FailingOtp()
    client = env["build"](otp_sender=failing)
    clock, conn = env["clock"], env["conn"]
    parent = sign_in(client, clock, "apple", "parent-sub")
    child = sign_in(client, clock, "google", "child-sub")
    family_id = new_family(client, parent["token"])
    invite = invite_child(client, parent["token"], family_id)
    assert accept(client, child["token"], invite["invite_secret"]).status_code == 200
    response = start_otp(client, child["token"], next_phone())
    assert response.status_code == 502
    assert response.json() == {"error": "sms_failed"}
    assert failing.tries == 1
    assert count(conn, "SELECT count(*) FROM phone_otp") == 1


def test_no_sender_means_otp_unavailable(env):
    client = env["build"](otp_sender=None)
    response = client.post("/v1/phones/otp", json={"phone_e164": next_phone()})
    assert response.status_code == 503
    assert response.json() == {"error": "otp_unavailable"}


# --- Parent confirm and reject ---


def test_confirm_needs_an_accepted_invite_and_a_verified_number(env):
    client, clock = env["client"], env["clock"]
    parent = sign_in(client, clock, "apple", "parent-sub")
    family_id = new_family(client, parent["token"])
    invite = invite_child(client, parent["token"], family_id)
    early = decide(client, parent["token"], family_id, invite["id"], "confirm")
    assert early.status_code == 409
    assert early.json() == {"error": "member_not_ready"}
    child = sign_in(client, clock, "google", "child-sub")
    assert accept(client, child["token"], invite["invite_secret"]).status_code == 200
    no_phone = decide(client, parent["token"], family_id, invite["id"], "confirm")
    assert no_phone.json() == {"error": "member_not_ready"}
    bad = decide(client, parent["token"], family_id, invite["id"], "maybe")
    assert bad.status_code == 400


def test_confirm_starts_the_24_hour_clock(env):
    clock, conn = env["clock"], env["conn"]
    clock.advance(timedelta(minutes=3))
    _parent, _child, _family_id, member_id, _phone = enrolled(env)
    row = conn.execute(
        """
        SELECT status, confirmed_by_parent_at, phone_current_since, phone_opted_in_at
        FROM family_members WHERE id = %s
        """,
        (member_id,),
    ).fetchone()
    assert row[0] == "active"
    assert row[1] == row[2] == clock.now()
    assert row[3] == clock.now()


def test_reject_removes_the_child_and_frees_the_number(env):
    client, clock, conn, sms = env["client"], env["clock"], env["conn"], env["sms"]
    parent, child, family_id, member_id, phone = enrolled(env, confirm=False)
    rejected = decide(client, parent["token"], family_id, member_id, "reject")
    assert rejected.status_code == 200
    assert rejected.json() == {"id": member_id, "status": "removed"}
    roster = client.get(f"/v1/families/{family_id}/members", headers=auth(parent["token"]))
    assert member_id not in roster.text
    assert open_case(client, parent["token"], member_id).status_code == 400
    assert start_otp(client, child["token"], next_phone()).json() == {"error": "not_a_child"}
    again = decide(client, parent["token"], family_id, member_id, "confirm")
    assert again.status_code == 404

    retry = invite_child(client, parent["token"], family_id, name="Minji again")
    newcomer = sign_in(client, clock, "google", "new-sub")
    assert accept(client, newcomer["token"], retry["invite_secret"]).status_code == 200
    assert start_otp(client, newcomer["token"], phone).status_code == 202
    assert check_otp(client, newcomer["token"], phone, sms.sent[-1][1]).status_code == 200
    assert "child_rejected" in {
        row[0]
        for row in conn.execute(
            "SELECT step FROM family_events WHERE family_id = %s", (family_id,)
        ).fetchall()
    }


def test_another_family_cannot_see_or_confirm(env):
    client, clock = env["client"], env["clock"]
    _parent, _child, family_id, member_id, _phone = enrolled(env, confirm=False)
    other = sign_in(client, clock, "apple", "other-parent")
    other_family = new_family(client, other["token"])
    assert client.get(
        f"/v1/families/{family_id}/members", headers=auth(other["token"])
    ).status_code == 404
    assert decide(client, other["token"], family_id, member_id, "confirm").status_code == 404
    assert decide(client, other["token"], other_family, member_id, "confirm").status_code == 404
    reissue = client.post(
        f"/v1/families/{family_id}/members/{member_id}/invite",
        headers=auth(other["token"]),
    )
    assert reissue.status_code == 404


def test_the_child_cannot_confirm_itself(env):
    client = env["client"]
    _parent, child, family_id, member_id, _phone = enrolled(env, confirm=False)
    response = decide(client, child["token"], family_id, member_id, "confirm")
    assert response.status_code == 404


def test_otp_codes_and_hashes_never_reach_a_response(env):
    client, conn = env["client"], env["conn"]
    parent, child, family_id, member_id, phone = enrolled(env, confirm=False)
    code_hash = conn.execute("SELECT code_hash FROM phone_otp").fetchone()[0]
    code = env["sms"].sent[-1][1]
    for response in (
        client.get(f"/v1/families/{family_id}/members", headers=auth(parent["token"])),
        decide(client, parent["token"], family_id, member_id, "confirm"),
    ):
        assert code_hash not in response.text
        assert code not in response.text
        assert phone not in response.text


def test_dev_login_still_works_beside_real_sign_in(env):
    client = env["client"]
    dev = login(client, "Dev parent")
    assert new_family(client, dev["token"])
