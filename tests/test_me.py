"""Milestone 12: what the Android parent app reads after sign-in.

`GET /v1/me` tells an app which family it belongs to, and
`GET /v1/families/{id}/cases` gives the parent's list of recent cases.

Readings, where the task text allows more than one:

- `/v1/me` works for any live session, parent or child, with or without a
  family. Memberships are the non-removed rows for that user, oldest first,
  each with the family name. No phone number, hash, salt, or invite.
- The case list is for an active parent of that family only. Anyone else,
  including an invited parent, a child of that family, and a parent of
  another family, gets 404 `not_found`, the same answer as an unknown id.
- The list is a summary: id, child, state, result, color, the claimed
  amount string or null, created and decided times, newest first. The
  suspicious text, transcript, claims object, pattern, timeline, phone,
  codes, and nonces stay on `GET /v1/cases/{id}` or nowhere.
- `limit` defaults to 20 and must be 1..50. Outside that, or not an
  integer, is 400 `invalid_body` (the request-validation answer), not a
  silent clamp.
"""

from datetime import timedelta
from uuid import UUID, uuid4

from backend.store import add_member, open_case
from test_api import (  # noqa: F401  (database_url, secrets, world are fixtures)
    NOW,
    _activate,
    _child,
    _family,
    _open,
    _set_dev_code,
    auth,
    database_url,
    login,
    next_phone,
    secrets,
    world,
)


ME_KEYS = {"user_id", "display_name", "locale", "memberships"}
MEMBERSHIP_KEYS = {"member_id", "family_id", "family_name", "role", "status", "display_name"}
CASE_KEYS = {
    "id",
    "child_member_id",
    "child_display_name",
    "state",
    "result",
    "color",
    "request_amount",
    "created_at",
    "decided_at",
}


def me(client, token):
    return client.get("/v1/me", headers=auth(token))


def cases(client, token, family_id, **params):
    return client.get(
        f"/v1/families/{family_id}/cases", headers=auth(token), params=params
    )


def callable_child(client, clock, token, family_id, name="민지", code="1357"):
    member_id = _child(client, token, family_id, name)
    activated = _activate(client, token, member_id, next_phone())
    assert activated.status_code == 201, activated.text
    assert _set_dev_code(client, token, member_id, code).status_code == 200
    return member_id


def seed_cases(conn, family_id, parent_user_id, child_member_id, count, start):
    """Cases written by the store, one second apart, so the per-day caps do not apply."""
    ids = []
    for index in range(count):
        ids.append(
            open_case(
                conn,
                family_id=UUID(family_id),
                opened_by=UUID(parent_user_id),
                child_member_id=UUID(child_member_id),
                parent_text=f"seeded text {index}",
                now=start + timedelta(seconds=index),
            )
        )
    conn.commit()
    return [str(case_id) for case_id in ids]


# --- GET /v1/me ---


def test_me_needs_a_session(world):
    client, _clock, _provider, _conn = world
    assert client.get("/v1/me").status_code == 401
    assert client.get("/v1/me").json() == {"error": "unauthorized"}
    assert me(client, "not-a-session-token-" + "x" * 20).status_code == 401


def test_me_without_a_family_has_no_memberships(world):
    client, _clock, _provider, _conn = world
    user = login(client, "Alone", locale="ko")
    response = me(client, user["token"])
    assert response.status_code == 200
    assert response.json() == {
        "user_id": user["user_id"],
        "display_name": "Alone",
        "locale": "ko",
        "memberships": [],
    }


def test_me_lists_the_parent_membership_with_the_family_name(world):
    client, _clock, _provider, _conn = world
    parent = login(client, "Mom")
    family_id = _family(client, parent["token"], name="Kim family")
    body = me(client, parent["token"]).json()
    assert set(body) == ME_KEYS
    assert body["user_id"] == parent["user_id"]
    assert body["display_name"] == "Mom"
    assert body["locale"] == "en"
    [membership] = body["memberships"]
    assert set(membership) == MEMBERSHIP_KEYS
    assert membership["family_id"] == family_id
    assert membership["family_name"] == "Kim family"
    assert membership["role"] == "parent"
    assert membership["status"] == "active"
    UUID(membership["member_id"])


def test_me_shows_an_invited_child_and_no_phone_or_hash(world):
    client, _clock, _provider, conn = world
    parent = login(client, "Mom")
    family_id = _family(client, parent["token"])
    invited = client.post(
        f"/v1/families/{family_id}/children",
        headers=auth(parent["token"]),
        json={"display_name": "민지"},
    ).json()
    child = login(client, "Minji", locale="ko")
    accepted = client.post(
        "/v1/invites/accept",
        headers=auth(child["token"]),
        json={"secret": invited["invite_secret"]},
    )
    assert accepted.status_code == 200, accepted.text
    response = me(client, child["token"])
    [membership] = response.json()["memberships"]
    assert membership == {
        "member_id": invited["id"],
        "family_id": family_id,
        "family_name": "Kim",
        "role": "child",
        "status": "invited",
        "display_name": "민지",
    }
    phone = next_phone("+82")
    assert _activate(client, parent["token"], invited["id"], phone, child["user_id"]).status_code == 201
    response = me(client, child["token"])
    assert response.json()["memberships"][0]["status"] == "active"
    stored = conn.execute(
        "SELECT code_hash, phone_e164 FROM family_members WHERE id = %s", (invited["id"],)
    ).fetchone()
    conn.rollback()
    for secret in (*stored, phone[-4:], invited["invite_secret"]):
        assert secret is None or secret not in response.text
    for word in ("phone", "hash", "salt", "invite", "token"):
        assert word not in response.text


def test_me_drops_removed_memberships_and_orders_the_rest_by_creation(world):
    client, clock, _provider, conn = world
    parent = login(client, "Mom")
    first = _family(client, parent["token"], name="First")
    clock.advance(timedelta(minutes=1))
    other = login(client, "Other parent")
    second = _family(client, other["token"], name="Second")
    third = _family(client, login(client, "Third parent")["token"], name="Third")
    user_id = UUID(parent["user_id"])
    add_member(
        conn, family_id=UUID(third), role="parent", display_name="Mom",
        now=NOW + timedelta(minutes=2), user_id=user_id, status="removed",
    )
    add_member(
        conn, family_id=UUID(second), role="parent", display_name="Mom too",
        now=NOW + timedelta(minutes=3), user_id=user_id, status="invited",
    )
    conn.commit()
    body = me(client, parent["token"]).json()
    assert [(m["family_name"], m["status"]) for m in body["memberships"]] == [
        ("First", "active"),
        ("Second", "invited"),
    ]
    assert body["memberships"][0]["family_id"] == first


def test_me_is_only_the_caller(world):
    client, _clock, _provider, _conn = world
    parent = login(client, "Mom")
    _family(client, parent["token"], name="Private")
    stranger = login(client, "Stranger")
    body = me(client, stranger["token"]).json()
    assert body["user_id"] == stranger["user_id"]
    assert body["memberships"] == []


# --- GET /v1/families/{id}/cases ---


def test_the_case_list_is_a_summary_newest_first(world):
    client, clock, _provider, conn = world
    parent = login(client, "Mom")
    family_id = _family(client, parent["token"])
    minji = callable_child(client, clock, parent["token"], family_id, "민지")
    jun = callable_child(client, clock, parent["token"], family_id, "Jun", code="2468")
    clock.advance(timedelta(hours=24))
    first = _open(client, parent["token"], minji, "secret text one 4155550199")
    assert first.status_code == 201, first.text
    clock.advance(timedelta(seconds=5))
    second = _open(client, parent["token"], jun, "secret text two")
    assert second.status_code == 201, second.text
    response = cases(client, parent["token"], family_id)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"family_id", "cases"}
    assert body["family_id"] == family_id
    listed = body["cases"]
    assert [row["id"] for row in listed] == [second.json()["id"], first.json()["id"]]
    for row in listed:
        assert set(row) == CASE_KEYS
        assert row["state"] == "calling"
        assert row["result"] is None
        assert row["color"] == "open"
        assert row["decided_at"] is None
    assert listed[0]["child_display_name"] == "Jun"
    assert listed[1]["child_display_name"] == "민지"
    assert listed[1]["child_member_id"] == minji
    assert listed[1]["created_at"] == (clock.now() - timedelta(seconds=5)).isoformat()
    for leaked in ("secret text", "4155550199", "1357", "2468", "parent_text", "transcript", "claims"):
        assert leaked not in response.text
    stored = conn.execute("SELECT code_hash FROM family_members WHERE id = %s", (minji,)).fetchone()
    conn.rollback()
    assert stored[0] not in response.text


def test_a_decided_case_shows_its_color_and_decided_time(world):
    client, clock, _provider, _conn = world
    parent = login(client, "Mom")
    family_id = _family(client, parent["token"])
    member_id = callable_child(client, clock, parent["token"], family_id)
    clock.advance(timedelta(hours=24))
    opened = _open(client, parent["token"], member_id).json()
    for digits in ("1357", "2"):
        client.post(
            f"/v1/dev/cases/{opened['id']}/digits",
            headers=auth(parent["token"]),
            json={"digits": digits},
        )
    [row] = cases(client, parent["token"], family_id).json()["cases"]
    assert row["state"] == "scam"
    assert row["color"] == "red"
    assert row["result"] is not None
    assert row["decided_at"] == clock.now().isoformat()


def test_only_an_active_parent_of_that_family_reads_the_list(world):
    client, clock, _provider, conn = world
    parent = login(client, "Mom")
    family_id = _family(client, parent["token"])
    member_id = callable_child(client, clock, parent["token"], family_id)
    clock.advance(timedelta(hours=24))
    assert _open(client, parent["token"], member_id).status_code == 201

    other_parent = login(client, "Other")
    _family(client, other_parent["token"], name="Other family")
    invited_parent = login(client, "Invited")
    add_member(
        conn, family_id=UUID(family_id), role="parent", display_name="Invited",
        now=NOW, user_id=UUID(invited_parent["user_id"]), status="invited",
    )
    removed_parent = login(client, "Removed")
    add_member(
        conn, family_id=UUID(family_id), role="parent", display_name="Removed",
        now=NOW, user_id=UUID(removed_parent["user_id"]), status="removed",
    )
    child = login(client, "Child")
    conn.execute(
        "UPDATE family_members SET user_id = %s WHERE id = %s",
        (UUID(child["user_id"]), UUID(member_id)),
    )
    conn.commit()
    for outsider in (other_parent, invited_parent, removed_parent, child, login(client, "Nobody")):
        response = cases(client, outsider["token"], family_id)
        assert response.status_code == 404
        assert response.json() == {"error": "not_found"}
    assert client.get(f"/v1/families/{family_id}/cases").status_code == 401
    for bad in (str(uuid4()), "not-a-uuid"):
        response = cases(client, parent["token"], bad)
        assert response.status_code == 404
        assert response.json() == {"error": "not_found"}


def test_another_familys_cases_are_not_in_the_list(world):
    client, clock, _provider, _conn = world
    mom = login(client, "Mom")
    mine = _family(client, mom["token"])
    other = login(client, "Other")
    theirs = _family(client, other["token"], name="Other")
    their_child = callable_child(client, clock, other["token"], theirs, "Theirs", code="2468")
    clock.advance(timedelta(hours=24))
    assert _open(client, other["token"], their_child).status_code == 201
    assert cases(client, mom["token"], mine).json()["cases"] == []
    assert len(cases(client, other["token"], theirs).json()["cases"]) == 1


def test_the_limit_defaults_to_20_and_stops_at_50(world):
    client, clock, _provider, conn = world
    parent = login(client, "Mom")
    family_id = _family(client, parent["token"])
    member_id = callable_child(client, clock, parent["token"], family_id)
    ids = seed_cases(conn, family_id, parent["user_id"], member_id, 55, NOW + timedelta(days=1))
    newest_first = list(reversed(ids))
    default = cases(client, parent["token"], family_id).json()["cases"]
    assert [row["id"] for row in default] == newest_first[:20]
    assert [row["id"] for row in cases(client, parent["token"], family_id, limit=1).json()["cases"]] == newest_first[:1]
    most = cases(client, parent["token"], family_id, limit=50).json()["cases"]
    assert [row["id"] for row in most] == newest_first[:50]
    assert "seeded text" not in str(most)
    for bad in (0, -1, 51, 1000, "ten", "1.5", ""):
        response = cases(client, parent["token"], family_id, limit=bad)
        assert response.status_code == 400, bad
        assert response.json() == {"error": "invalid_body"}


def test_cases_with_the_same_created_at_have_a_stable_order(world):
    client, clock, _provider, conn = world
    parent = login(client, "Mom")
    family_id = _family(client, parent["token"])
    member_id = callable_child(client, clock, parent["token"], family_id)
    at = NOW + timedelta(days=1)
    for index in range(4):
        open_case(
            conn, family_id=UUID(family_id), opened_by=UUID(parent["user_id"]),
            child_member_id=UUID(member_id), parent_text="same moment", now=at,
        )
    conn.commit()
    first = [row["id"] for row in cases(client, parent["token"], family_id).json()["cases"]]
    second = [row["id"] for row in cases(client, parent["token"], family_id).json()["cases"]]
    assert first == second == sorted(first, reverse=True)
