"""Tests for the milestone-3 schema and store.

The contract is docs/PRODUCT_REDESIGN.md, sections "Data model" and
"M3. Schema and store". Postgres comes from docker-compose.yml. If it is
not accepting connections, the database tests skip and the message includes
`docker compose up -d`.

Readings these tests lock, where the milestone text allows more than one:

- `opened_by` and `families.created_by` reference `users`. The child is a
  `family_members` row, and that row's family must be the case's family.
- `deadline_at` follows the state just entered: 90s `waiting_push`, 180s
  `calling`, 45s `awaiting_answer`, and null once the case is terminal.
  `call_accepted` does not move it and inserts no timeline row. The timer
  table starts the code window at `call_accepted`; arming it on entry to
  `calling` is what keeps a case from sitting open when that event never
  arrives. A later `call_accepted` does not extend the window.
- `slow_checks` is not a column. It is the count of `code_check_slow`
  timeline rows for that case.
- `static_locked` is `codes.static_code_locked` over
  `case_events.step = static_code_mismatch` for that child, across cases.
  The row stores the outcome, not the digits. The fifth mismatch is still
  `wrong`. The next attempt is `code_locked` and does not dial.
- `has_app` is `user_id is not None`. `has_push_token` is a non-empty
  token. `has_opted_in_phone` needs both `phone_e164` and
  `phone_opted_in_at`. Status and `confirmed_by_parent_at` are not folded
  into those flags.
- `number_recent` is `phone_current_since` strictly less than 24 hours
  before `now`. At exactly 24 hours a keypad yes can be green.
- A one-time code is not stored. The row keeps a 16-byte nonce, the
  pepper hash, expiry, and used-at. `call_code` derives the digits from
  the nonce and `OTP_DERIVATION_KEY`, so another connection derives the
  same digits. A re-issue replaces the nonce. Expiry and single use stay
  on the row. Keypad checks still use the stored hash.
- One timeline row per transition that changes the case. The step is the
  submission's timeline step when it has one, otherwise the event name.
  A no-op, including a second event on a terminal case, writes nothing.
- The store does not commit. The caller owns the transaction.
- OTP completion rejects an E.164 that is already some non-removed
  member's `phone_e164` or `pending_phone_e164`. The first completion
  sets `phone_opted_in_at` and leaves `phone_current_since` null. Country
  allow-lists stay in the API: `+44` is a legal E.164 here.
- Empty static digits follow `submission_event` and record nothing.
"""

import ast
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

from backend.codes import derive_one_time, hash_one_time
from backend.store import (
    ANSWER_WINDOW,
    CODE_WINDOW,
    NUMBER_RECENT_WINDOW,
    PUSH_WINDOW,
    CaseNotFound,
    PhoneInUse,
    add_member,
    apply_case,
    apply_schema,
    call_code,
    complete_phone_otp,
    create_family,
    create_user,
    deadline_for,
    load_case,
    member_flags,
    open_case,
    reissue_one_time,
    set_check_code,
    submit_digits,
)


COMPOSE_COMMAND = "docker compose up -d"
SCHEMA = Path("backend/schema.sql")
COMPOSE = Path("docker-compose.yml")
ROOT = Path(__file__).resolve().parents[1]
TEST_SCHEMA = "familyshield_test"
NOW = datetime(2026, 11, 3, 3, 0, tzinfo=timezone.utc)
CODE_SET = NOW - timedelta(days=3)
STATIC_CODE = "1357"
PEPPER = "test-pepper-0123456789"
DERIVATION_KEY = "test-derivation-key-0123456789"
NONCE = b"\x42" * 16

TABLES = {
    "users": {
        "id",
        "auth_provider",
        "auth_subject",
        "display_name",
        "locale",
        "created_at",
    },
    "sessions": {"id", "user_id", "token_hash", "expires_at", "revoked_at"},
    "families": {"id", "name", "created_by", "created_at"},
    "family_members": {
        "id",
        "family_id",
        "user_id",
        "role",
        "display_name",
        "status",
        "phone_e164",
        "phone_opted_in_at",
        "phone_current_since",
        "pending_phone_e164",
        "pending_phone_set_at",
        "push_token",
        "push_provider",
        "push_env",
        "code_hash",
        "code_salt",
        "code_set_at",
        "invite_hash",
        "invite_expires_at",
        "confirmed_by_parent_at",
        "created_at",
    },
    "cases": {
        "id",
        "family_id",
        "opened_by",
        "child_member_id",
        "state",
        "result",
        "answered_via",
        "parent_text",
        "transcript",
        "claims",
        "pattern_id",
        "code_channel",
        "one_time_nonce",
        "one_time_code_hash",
        "one_time_code_expires_at",
        "one_time_code_used_at",
        "deadline_at",
        "audio_deleted_at",
        "created_at",
        "updated_at",
        "decided_at",
    },
    "verification_attempts": {
        "id",
        "case_id",
        "channel",
        "status",
        "provider",
        "provider_ref",
        "started_at",
        "ended_at",
    },
    "case_events": {"id", "seq", "case_id", "at", "step"},
    "family_events": {"id", "seq", "family_id", "at", "actor_user_id", "step"},
    "phone_otp": {
        "id",
        "member_id",
        "phone_e164",
        "code_hash",
        "expires_at",
        "attempts",
        "consumed_at",
        "created_at",
    },
}

TIMESTAMPTZ = {
    ("users", "created_at"),
    ("sessions", "expires_at"),
    ("sessions", "revoked_at"),
    ("families", "created_at"),
    ("family_members", "phone_opted_in_at"),
    ("family_members", "phone_current_since"),
    ("family_members", "pending_phone_set_at"),
    ("family_members", "code_set_at"),
    ("family_members", "invite_expires_at"),
    ("family_members", "confirmed_by_parent_at"),
    ("family_members", "created_at"),
    ("cases", "one_time_code_expires_at"),
    ("cases", "one_time_code_used_at"),
    ("cases", "deadline_at"),
    ("cases", "audio_deleted_at"),
    ("cases", "created_at"),
    ("cases", "updated_at"),
    ("cases", "decided_at"),
    ("verification_attempts", "started_at"),
    ("verification_attempts", "ended_at"),
    ("case_events", "at"),
    ("family_events", "at"),
    ("phone_otp", "expires_at"),
    ("phone_otp", "consumed_at"),
    ("phone_otp", "created_at"),
}

FORBIDDEN_COLUMNS = {
    "code_misses",
    "slow_checks",
    "digits",
    "plaintext",
    "one_time_code",
    "check_code",
    "static_code",
    "code",
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


@pytest.fixture
def conn(database_url):
    connection = _connect(database_url)
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


@pytest.fixture(autouse=True)
def pepper(monkeypatch):
    monkeypatch.setenv("CODE_PEPPER", PEPPER)
    monkeypatch.setenv("OTP_DERIVATION_KEY", DERIVATION_KEY)


def next_phone(country: str = "+1") -> str:
    global _phone_n
    _phone_n += 1
    if country == "+82":
        return f"+8210{_phone_n:08d}"
    return f"+1415{_phone_n:07d}"


def fixed_salt(n: int) -> bytes:
    return b"\x22" * n


def fixed_rng(n: int) -> bytes:
    return b"\x42" * n


def one_time_digits(case_id) -> str:
    return derive_one_time(case_id, NONCE)


def seed(
    conn,
    *,
    now=NOW,
    app=False,
    push=False,
    phone=True,
    opted_in=True,
    established=True,
    phone_current_since=None,
    since_given=False,
    status="active",
    confirmed=True,
    country="+1",
    static=False,
):
    parent = create_user(
        conn,
        auth_provider="apple",
        auth_subject=f"parent-{uuid4()}",
        display_name="Parent",
        locale="en",
        now=now,
    )
    family = create_family(conn, name="Kim", created_by=parent, now=now)
    child_user = None
    if app:
        child_user = create_user(
            conn,
            auth_provider="google",
            auth_subject=f"child-{uuid4()}",
            display_name="Minji",
            locale="ko",
            now=now,
        )
    number = next_phone(country) if phone else None
    if since_given:
        since = phone_current_since
    elif phone and opted_in and established:
        since = now - timedelta(days=2)
    else:
        since = None
    member = add_member(
        conn,
        family_id=family,
        role="child",
        display_name="Minji",
        now=now,
        user_id=child_user,
        status=status,
        phone_e164=number,
        phone_opted_in_at=now if phone and opted_in else None,
        phone_current_since=since,
        push_token="device-token" if push else None,
        push_provider="apns" if push else None,
        push_env="production" if push else None,
        confirmed_by_parent_at=now if confirmed else None,
    )
    if static:
        set_check_code(
            conn,
            member,
            STATIC_CODE,
            now=CODE_SET,
            biometric_ok=False,
            rng=fixed_salt,
        )
    case = open_case(
        conn,
        family_id=family,
        opened_by=parent,
        child_member_id=member,
        parent_text="please send money",
        now=now,
    )
    return {
        "parent": parent,
        "family": family,
        "member": member,
        "case": case,
        "phone": number,
        "child_user": child_user,
    }


def assert_rejected(conn, sql, params=()):
    with pytest.raises(psycopg.IntegrityError):
        with conn.transaction():
            conn.execute(sql, params)


def columns(conn):
    rows = conn.execute(
        """
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = %s
        """,
        (TEST_SCHEMA,),
    ).fetchall()
    found = {}
    types = {}
    for table, column, data_type in rows:
        found.setdefault(table, set()).add(column)
        types[(table, column)] = data_type
    return found, types


def case_text(conn, case_id) -> str:
    row = conn.execute(
        """
        SELECT state, result::text, answered_via::text, code_channel::text,
               parent_text, transcript, pattern_id
        FROM cases WHERE id = %s
        """,
        (case_id,),
    ).fetchone()
    steps = conn.execute(
        "SELECT step FROM case_events WHERE case_id = %s",
        (case_id,),
    ).fetchall()
    parts = [str(value) for value in row if value is not None]
    parts.extend(step for (step,) in steps)
    return "\n".join(parts)


# --- Files the milestone names, no database ---


def test_schema_comment_repeats_the_compose_command():
    text = SCHEMA.read_text()
    assert COMPOSE_COMMAND in text
    assert "no SQLite schema" in text
    assert "code_misses" not in text
    assert "slow_checks" not in text


def test_skip_message_includes_the_compose_command():
    message = _skip_reason(ConnectionError("connection refused"))
    assert COMPOSE_COMMAND in message
    assert "connection refused" in message


def test_compose_file_is_the_postgres_test_setup():
    text = COMPOSE.read_text()
    assert "postgres:16" in text
    assert "familyshield" in text
    assert "5432" in text


def test_requirements_pin_the_postgres_driver():
    text = (ROOT / "requirements.txt").read_text()
    assert "psycopg[binary]==" in text


def test_env_example_has_a_database_url_placeholder():
    text = (ROOT / ".env.example").read_text()
    assert "\nDATABASE_URL=\n" in text or text.endswith("DATABASE_URL=\n")
    assert "\nOTP_DERIVATION_KEY=\n" in text
    assert "postgresql://familyshield:familyshield" not in text


def test_store_does_not_read_the_clock_or_talk_to_providers():
    source = (ROOT / "backend" / "store.py").read_text()
    tree = ast.parse(source)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module.split(".")[0])
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {
                "now",
                "utcnow",
                "randbelow",
                "token_bytes",
                "token_hex",
                "token_urlsafe",
            }
    assert "secrets" not in imported
    assert "_CALL_CODES" not in source
    assert "clear_call_codes" not in source
    for banned in ("twilio", "anthropic", "requests", "cartesia", "sqlite3", "httpx"):
        assert banned not in imported


def test_deadline_follows_the_state_just_entered():
    assert deadline_for("waiting_push", NOW) == NOW + PUSH_WINDOW
    assert deadline_for("calling", NOW) == NOW + CODE_WINDOW
    assert deadline_for("awaiting_answer", NOW) == NOW + ANSWER_WINDOW
    assert PUSH_WINDOW == timedelta(seconds=90)
    assert CODE_WINDOW == timedelta(seconds=180)
    assert ANSWER_WINDOW == timedelta(seconds=45)
    assert NUMBER_RECENT_WINDOW == timedelta(hours=24)
    for state in ("opened", "confirmed", "scam", "not_confirmed"):
        assert deadline_for(state, NOW) is None


def test_deadline_rejects_a_naive_clock():
    with pytest.raises(ValueError):
        deadline_for("calling", datetime(2026, 11, 3, 3, 0))


def test_member_flags_copy_the_columns_the_milestone_names():
    member = {
        "user_id": uuid4(),
        "push_token": "abc",
        "phone_e164": "+14155550123",
        "phone_opted_in_at": NOW - timedelta(days=3),
        "phone_current_since": NOW - timedelta(hours=23, minutes=59),
        "code_set_at": CODE_SET,
    }
    flags = member_flags(member, [], now=NOW)
    assert flags == {
        "has_app": True,
        "has_push_token": True,
        "has_opted_in_phone": True,
        "number_recent": True,
        "static_locked": False,
    }


def test_flags_are_false_when_the_columns_are_missing():
    flags = member_flags(
        {
            "user_id": None,
            "push_token": None,
            "phone_e164": "+14155550123",
            "phone_opted_in_at": None,
            "phone_current_since": None,
            "code_set_at": None,
        },
        [],
        now=NOW,
    )
    assert flags["has_app"] is False
    assert flags["has_push_token"] is False
    assert flags["has_opted_in_phone"] is False
    assert flags["number_recent"] is False
    assert flags["static_locked"] is False


def test_number_recent_is_false_at_exactly_24_hours():
    member = {
        "user_id": None,
        "push_token": " ",
        "phone_e164": "+14155550123",
        "phone_opted_in_at": NOW,
        "phone_current_since": NOW - NUMBER_RECENT_WINDOW,
        "code_set_at": None,
    }
    flags = member_flags(member, [], now=NOW)
    assert flags["number_recent"] is False
    assert flags["has_push_token"] is False


def test_five_static_mismatches_since_the_code_was_set_lock_it():
    set_at = NOW - timedelta(hours=2)
    misses = [NOW - timedelta(minutes=index + 1) for index in range(5)]
    assert member_flags(
        _bare_member(code_set_at=set_at), misses, now=NOW
    )["static_locked"] is True
    assert member_flags(
        _bare_member(code_set_at=set_at), misses[:4], now=NOW
    )["static_locked"] is False


def test_mismatches_at_or_before_code_set_at_do_not_lock():
    set_at = NOW - timedelta(hours=1)
    misses = [set_at - timedelta(minutes=index) for index in range(5)]
    misses.append(set_at)
    assert member_flags(
        _bare_member(code_set_at=set_at), misses, now=NOW
    )["static_locked"] is False


def _bare_member(**overrides):
    member = {
        "user_id": None,
        "push_token": None,
        "phone_e164": None,
        "phone_opted_in_at": None,
        "phone_current_since": None,
        "code_set_at": None,
    }
    member.update(overrides)
    return member


# --- Schema ---


def test_schema_tables_and_columns_match_the_data_model(conn):
    found, types = columns(conn)
    assert set(found) == set(TABLES)
    for table, expected in TABLES.items():
        assert found[table] == expected
    for key in TIMESTAMPTZ:
        assert types[key] == "timestamp with time zone", key
    assert types[("cases", "claims")] == "jsonb"
    assert types[("cases", "id")] == "uuid"
    assert types[("family_members", "code_salt")] == "bytea"
    assert types[("cases", "one_time_nonce")] == "bytea"
    flat = {column for names in found.values() for column in names}
    assert FORBIDDEN_COLUMNS.isdisjoint(flat)


def test_indexes_the_milestone_names(conn):
    rows = conn.execute(
        """
        SELECT indexdef FROM pg_indexes
        WHERE schemaname = %s
        """,
        (TEST_SCHEMA,),
    ).fetchall()
    defs = "\n".join(row[0] for row in rows)
    assert "child_member_id" in defs and "created_at" in defs
    assert "deadline_at" in defs
    assert "(family_id, status)" in defs
    assert "UNIQUE INDEX" in defs
    phone = [
        line
        for line in defs.splitlines()
        if re.search(r"\bphone_e164\b", line) and "UNIQUE" in line
    ]
    pending = [
        line
        for line in defs.splitlines()
        if re.search(r"\bpending_phone_e164\b", line) and "UNIQUE" in line
    ]
    assert len(phone) == 1
    assert len(pending) == 1
    assert "removed" in phone[0]
    assert "removed" in pending[0]


def test_unique_phone_ignores_removed_members(conn):
    first = seed(conn, phone=True)
    second_parent = create_user(
        conn,
        auth_provider="google",
        auth_subject=f"other-{uuid4()}",
        display_name="Other",
        locale="ko",
        now=NOW,
    )
    other = create_family(conn, name="Other", created_by=second_parent, now=NOW)
    assert_rejected(
        conn,
        """
        INSERT INTO family_members (
            family_id, role, display_name, status, phone_e164, created_at
        ) VALUES (%s, 'child', 'Other', 'invited', %s, %s)
        """,
        (other, first["phone"], NOW),
    )
    conn.execute(
        "UPDATE family_members SET status = 'removed' WHERE id = %s",
        (first["member"],),
    )
    add_member(
        conn,
        family_id=other,
        role="child",
        display_name="Other",
        now=NOW,
        phone_e164=first["phone"],
    )


def test_plaintext_codes_do_not_fit_the_hash_columns(conn):
    ids = seed(conn)
    assert_rejected(
        conn,
        "UPDATE family_members SET code_hash = '2580', code_salt = %s, code_set_at = %s WHERE id = %s",
        (b"\x11" * 16, NOW, ids["member"]),
    )
    assert_rejected(
        conn,
        "UPDATE cases SET one_time_code_hash = '135790', one_time_code_expires_at = %s WHERE id = %s",
        (NOW, ids["case"]),
    )
    assert_rejected(
        conn,
        """
        INSERT INTO phone_otp (member_id, phone_e164, code_hash, expires_at, created_at)
        VALUES (%s, %s, '123456', %s, %s)
        """,
        (ids["member"], ids["phone"], NOW, NOW),
    )


def test_parent_cannot_store_a_check_code(conn):
    ids = seed(conn)
    parent_member = add_member(
        conn,
        family_id=ids["family"],
        role="parent",
        display_name="Parent",
        now=NOW,
        user_id=ids["parent"],
        status="active",
    )
    assert_rejected(
        conn,
        """
        UPDATE family_members
        SET code_hash = %s, code_salt = %s, code_set_at = %s
        WHERE id = %s
        """,
        ("$argon2id$v=19$m=1,t=1,p=1$c2FsdA$aaaa", b"\x11" * 16, NOW, parent_member),
    )


def test_case_cannot_point_at_a_child_in_another_family(conn):
    first = seed(conn)
    second = seed(conn)
    assert_rejected(
        conn,
        """
        UPDATE cases SET family_id = %s WHERE id = %s
        """,
        (second["family"], first["case"]),
    )


def test_enums_and_result_match_the_state(conn):
    ids = seed(conn)
    assert_rejected(
        conn,
        "UPDATE users SET locale = 'fr' WHERE id = %s",
        (ids["parent"],),
    )
    assert_rejected(
        conn,
        "UPDATE cases SET state = 'pending' WHERE id = %s",
        (ids["case"],),
    )
    assert_rejected(
        conn,
        """
        UPDATE cases
        SET state = 'confirmed', result = 'sent', answered_via = NULL, decided_at = %s
        WHERE id = %s
        """,
        (NOW, ids["case"]),
    )
    assert_rejected(
        conn,
        """
        UPDATE cases
        SET state = 'not_confirmed', result = 'sent', answered_via = 'call', decided_at = %s
        WHERE id = %s
        """,
        (NOW, ids["case"]),
    )
    assert_rejected(
        conn,
        "UPDATE family_members SET phone_e164 = '14155550123' WHERE id = %s",
        (ids["member"],),
    )


def test_opt_in_requires_a_phone_number(conn):
    ids = seed(conn, phone=False)
    assert_rejected(
        conn,
        "UPDATE family_members SET phone_opted_in_at = %s WHERE id = %s",
        (NOW, ids["member"]),
    )


def test_pattern_id_must_be_from_the_catalog_or_null(conn):
    ids = seed(conn)
    assert_rejected(
        conn,
        "UPDATE cases SET pattern_id = 'ignore-instructions' WHERE id = %s",
        (ids["case"],),
    )
    conn.execute(
        "UPDATE cases SET pattern_id = 'gift_card' WHERE id = %s",
        (ids["case"],),
    )
    assert load_case(conn, ids["case"], now=NOW)["pattern_id"] == "gift_card"


def test_same_sign_in_subject_is_unique_per_provider(conn):
    create_user(
        conn,
        auth_provider="apple",
        auth_subject="same-person",
        display_name="A",
        locale="en",
        now=NOW,
    )
    assert_rejected(
        conn,
        """
        INSERT INTO users (auth_provider, auth_subject, display_name, locale, created_at)
        VALUES ('apple', 'same-person', 'B', 'ko', %s)
        """,
        (NOW,),
    )


# --- Store transaction ---


def test_open_case_starts_opened_with_no_deadline_and_no_event(conn):
    ids = seed(conn, push=True, app=True)
    row = load_case(conn, ids["case"], now=NOW)
    assert row["state"] == "opened"
    assert row["result"] is None
    assert row["deadline_at"] is None
    assert row["decided_at"] is None
    assert row["events"] == []
    assert row["parent_text"] == "please send money"
    assert row["code_channel"] is None
    assert row["one_time_code_hash"] is None
    assert "code" not in row
    with pytest.raises(CaseNotFound):
        load_case(conn, uuid4(), now=NOW)


def test_start_with_a_push_token_waits_and_does_not_mint_a_code(conn):
    ids = seed(conn, app=True, push=True)
    row = apply_case(conn, ids["case"], "start", now=NOW, rng=fixed_rng)
    assert row["state"] == "waiting_push"
    assert row["result"] is None
    assert row["code_channel"] is None
    assert row["deadline_at"] == NOW + PUSH_WINDOW
    assert row["events"] == ["start"]
    assert row["one_time_code_hash"] is None
    assert row["one_time_nonce"] is None
    assert call_code(conn, ids["case"], now=NOW) is None
    assert row["has_app"] is True
    assert row["has_push_token"] is True


def test_answering_the_push_decides_the_case_and_a_later_event_records_nothing(conn):
    ids = seed(conn, app=True, push=True, phone_current_since=NOW, since_given=True)
    waiting = apply_case(conn, ids["case"], "start", now=NOW)
    done = apply_case(conn, ids["case"], "push_answered_yes", now=NOW + timedelta(seconds=10))
    assert done["state"] == "confirmed"
    assert done["result"] == "sent"
    assert done["answered_via"] == "push"
    assert done["number_recent"] is True
    assert done["deadline_at"] is None
    assert done["decided_at"] == NOW + timedelta(seconds=10)
    assert done["events"] == ["start", "push_answered_yes"]
    updated_at = done["updated_at"]
    again = apply_case(
        conn, ids["case"], "answer_no", now=NOW + timedelta(seconds=30)
    )
    assert again["state"] == "confirmed"
    assert again["result"] == "sent"
    assert again["events"] == ["start", "push_answered_yes"]
    assert again["updated_at"] == updated_at
    assert again["decided_at"] == done["decided_at"]
    assert waiting["deadline_at"] == NOW + PUSH_WINDOW


def test_start_with_nothing_reachable_is_no_number(conn):
    ids = seed(conn, phone=False, push=False, app=False, established=False)
    row = apply_case(conn, ids["case"], "start", now=NOW)
    assert row["state"] == "not_confirmed"
    assert row["result"] == "no_number"
    assert row["code_channel"] is None
    assert row["deadline_at"] is None
    assert row["decided_at"] == NOW
    assert row["events"] == ["start"]


def test_a_phone_without_opt_in_is_not_dialed(conn):
    ids = seed(conn, phone=True, opted_in=False, push=False, established=False)
    row = apply_case(conn, ids["case"], "start", now=NOW)
    assert row["has_opted_in_phone"] is False
    assert row["result"] == "no_number"


def test_flags_are_read_when_the_event_is_applied(conn):
    ids = seed(conn, app=True, push=True)
    conn.execute(
        """
        UPDATE family_members
        SET push_token = NULL, push_provider = NULL, push_env = NULL,
            phone_e164 = NULL, phone_opted_in_at = NULL, phone_current_since = NULL
        WHERE id = %s
        """,
        (ids["member"],),
    )
    row = apply_case(conn, ids["case"], "start", now=NOW)
    assert row["has_push_token"] is False
    assert row["has_app"] is True
    assert row["result"] == "no_number"


def test_call_only_child_enters_calling_on_the_static_channel(conn):
    ids = seed(conn, app=False, push=False, static=True)
    row = apply_case(conn, ids["case"], "start", now=NOW, rng=fixed_rng)
    assert row["state"] == "calling"
    assert row["code_channel"] == "static"
    assert row["has_app"] is False
    assert row["deadline_at"] == NOW + CODE_WINDOW
    assert row["one_time_code_hash"] is None
    assert row["one_time_nonce"] is None
    assert row["events"] == ["start"]
    assert STATIC_CODE not in case_text(conn, ids["case"])


def test_app_child_without_a_token_gets_one_one_time_code(conn):
    ids = seed(conn, app=True, push=False, country="+82")
    row = apply_case(conn, ids["case"], "start", now=NOW, rng=fixed_rng)
    code = one_time_digits(ids["case"])
    assert row["state"] == "calling"
    assert row["code_channel"] == "one_time"
    assert row["deadline_at"] == NOW + CODE_WINDOW
    assert bytes(row["one_time_nonce"]) == NONCE
    assert row["one_time_code_hash"] == hash_one_time(code)
    assert row["one_time_code_expires_at"] == NOW + timedelta(minutes=5)
    assert row["one_time_code_used_at"] is None
    assert call_code(conn, ids["case"], now=NOW) == code
    assert code not in case_text(conn, ids["case"])
    assert code.encode() not in bytes(row["one_time_nonce"])
    assert ids["phone"].startswith("+82")
    stored = conn.execute(
        "SELECT one_time_code_hash, one_time_nonce FROM cases WHERE id = %s",
        (ids["case"],),
    ).fetchone()
    again = apply_case(
        conn,
        ids["case"],
        "call_accepted",
        now=NOW + timedelta(seconds=5),
        rng=lambda n: b"\x99" * n,
    )
    assert again["events"] == ["start"]
    assert again["deadline_at"] == NOW + CODE_WINDOW
    assert again["updated_at"] == row["updated_at"]
    assert again["one_time_code_hash"] == stored[0]
    assert bytes(again["one_time_nonce"]) == bytes(stored[1])
    assert call_code(conn, ids["case"], now=NOW) == code


def test_a_restart_derives_the_same_code_and_use_hides_it(conn, database_url):
    ids = seed(conn, app=True, push=False)
    apply_case(conn, ids["case"], "start", now=NOW, rng=fixed_rng)
    code = one_time_digits(ids["case"])
    hashed = load_case(conn, ids["case"], now=NOW)["one_time_code_hash"]
    conn.commit()
    other = _connect(database_url)
    try:
        assert call_code(other, ids["case"], now=NOW) == code
        assert call_code(conn, ids["case"], now=NOW) == code
        accepted = submit_digits(conn, ids["case"], code, now=NOW)
        conn.commit()
        assert accepted["state"] == "awaiting_answer"
        assert accepted["one_time_code_hash"] == hashed
        assert accepted["one_time_code_used_at"] == NOW
        assert call_code(other, ids["case"], now=NOW) is None
        assert bytes(accepted["one_time_nonce"]) == NONCE
    finally:
        other.close()
        _delete_user_graph(database_url)


def test_expiry_hides_the_code_and_the_nonce_stays(conn):
    ids = seed(conn, app=True, push=False)
    issued = apply_case(conn, ids["case"], "start", now=NOW, rng=fixed_rng)
    assert call_code(conn, ids["case"], now=issued["one_time_code_expires_at"]) is None
    stored = conn.execute(
        "SELECT one_time_nonce, one_time_code_hash FROM cases WHERE id = %s",
        (ids["case"],),
    ).fetchone()
    assert bytes(stored[0]) == NONCE
    assert stored[1] == issued["one_time_code_hash"]


def test_push_window_with_an_app_places_one_call_and_one_code(conn):
    ids = seed(conn, app=True, push=True)
    apply_case(conn, ids["case"], "start", now=NOW)
    row = apply_case(
        conn,
        ids["case"],
        "push_window_elapsed",
        now=NOW + PUSH_WINDOW,
        rng=fixed_rng,
    )
    code = one_time_digits(ids["case"])
    assert row["state"] == "calling"
    assert row["code_channel"] == "one_time"
    assert row["deadline_at"] == NOW + PUSH_WINDOW + CODE_WINDOW
    assert row["one_time_code_hash"] == hash_one_time(code)
    assert call_code(conn, ids["case"], now=NOW + PUSH_WINDOW) == code


def test_push_failure_without_a_phone_is_unreachable_and_mints_no_code(conn):
    ids = seed(conn, app=True, push=True, phone=False, established=False)
    apply_case(conn, ids["case"], "start", now=NOW)
    row = apply_case(conn, ids["case"], "push_failed", now=NOW, rng=fixed_rng)
    assert row["result"] == "unreachable"
    assert row["one_time_code_hash"] is None


def test_push_window_without_a_phone_is_timeout(conn):
    ids = seed(conn, app=False, push=True, phone=False, established=False)
    apply_case(conn, ids["case"], "start", now=NOW)
    row = apply_case(conn, ids["case"], "push_window_elapsed", now=NOW + PUSH_WINDOW)
    assert row["result"] == "timeout"
    assert row["result"] != "not_sent"


def test_locked_static_code_does_not_dial(conn):
    ids = seed(conn, app=False, push=False, static=True)
    _mismatch_until_locked(conn, ids)
    later = NOW + timedelta(minutes=1)
    case = open_case(
        conn,
        family_id=ids["family"],
        opened_by=ids["parent"],
        child_member_id=ids["member"],
        parent_text="",
        now=later,
    )
    row = apply_case(conn, case, "start", now=later)
    assert row["state"] == "not_confirmed"
    assert row["result"] == "code_locked"
    assert row["code_channel"] is None
    assert row["state"] != "calling"


def test_the_fifth_static_mismatch_is_wrong_and_the_next_attempt_is_locked(conn):
    ids = seed(conn, app=False, push=False, static=True)
    last = None
    for index in range(5):
        case = ids["case"] if index == 0 else open_case(
            conn,
            family_id=ids["family"],
            opened_by=ids["parent"],
            child_member_id=ids["member"],
            parent_text="",
            now=NOW,
        )
        apply_case(conn, case, "start", now=NOW + timedelta(seconds=index))
        last = submit_digits(
            conn, case, "0000", now=NOW + timedelta(seconds=index, microseconds=1)
        )
        assert last["result"] == "wrong"
        assert last["events"][-1] == "static_code_mismatch"
        assert "0000" not in case_text(conn, case)
    assert last["static_locked"] is True
    nxt = open_case(
        conn,
        family_id=ids["family"],
        opened_by=ids["parent"],
        child_member_id=ids["member"],
        parent_text="",
        now=NOW,
    )
    blocked = apply_case(conn, nxt, "start", now=NOW + timedelta(minutes=1))
    assert blocked["result"] == "code_locked"
    assert blocked["code_channel"] is None


def test_a_new_check_code_clears_the_lock_without_deleting_rows(conn):
    ids = seed(conn, app=False, push=False, static=True)
    _mismatch_until_locked(conn, ids)
    kept = conn.execute(
        """
        SELECT count(*) FROM case_events
        WHERE step = 'static_code_mismatch'
          AND case_id IN (SELECT id FROM cases WHERE child_member_id = %s)
        """,
        (ids["member"],),
    ).fetchone()[0]
    assert kept >= 5
    set_check_code(
        conn,
        ids["member"],
        "2468",
        now=NOW + timedelta(minutes=5),
        biometric_ok=True,
        rng=lambda n: b"\x33" * n,
    )
    case = open_case(
        conn,
        family_id=ids["family"],
        opened_by=ids["parent"],
        child_member_id=ids["member"],
        parent_text="",
        now=NOW + timedelta(minutes=5),
    )
    row = apply_case(conn, case, "start", now=NOW + timedelta(minutes=5))
    assert row["state"] == "calling"
    assert row["code_channel"] == "static"
    assert row["static_locked"] is False
    stored = conn.execute(
        "SELECT code_hash, code_salt FROM family_members WHERE id = %s",
        (ids["member"],),
    ).fetchone()
    assert stored[0].startswith("$argon2id$")
    assert stored[0] != "2468"
    assert bytes(stored[1]) == b"\x33" * 16


def test_mismatches_older_than_24_hours_do_not_lock(conn):
    ids = seed(conn, app=False, push=False, static=True)
    # The whole cluster sits outside the 24-hour window, including the
    # few seconds between the five submissions.
    old = NOW - timedelta(hours=25)
    for index in range(5):
        case = ids["case"] if index == 0 else open_case(
            conn,
            family_id=ids["family"],
            opened_by=ids["parent"],
            child_member_id=ids["member"],
            parent_text="",
            now=old,
        )
        apply_case(conn, case, "start", now=old + timedelta(seconds=index))
        submit_digits(
            conn,
            case,
            "0000",
            now=old + timedelta(seconds=index, microseconds=1),
        )
    case = open_case(
        conn,
        family_id=ids["family"],
        opened_by=ids["parent"],
        child_member_id=ids["member"],
        parent_text="",
        now=NOW,
    )
    row = apply_case(conn, case, "start", now=NOW)
    assert row["state"] == "calling"
    assert row["static_locked"] is False


def test_a_mismatch_exactly_24_hours_old_still_counts(conn):
    ids = seed(conn, app=False, push=False, static=True)
    at = NOW - NUMBER_RECENT_WINDOW
    for index in range(5):
        case = ids["case"] if index == 0 else open_case(
            conn,
            family_id=ids["family"],
            opened_by=ids["parent"],
            child_member_id=ids["member"],
            parent_text="",
            now=at,
        )
        moment = at + timedelta(microseconds=index)
        apply_case(conn, case, "start", now=moment)
        submit_digits(conn, case, "0000", now=moment)
    case = open_case(
        conn,
        family_id=ids["family"],
        opened_by=ids["parent"],
        child_member_id=ids["member"],
        parent_text="",
        now=NOW,
    )
    row = apply_case(conn, case, "start", now=NOW)
    assert row["result"] == "code_locked"


def test_one_time_misses_do_not_lock_the_static_code(conn):
    ids = seed(conn, app=True, push=False, static=True)
    for index in range(5):
        case = ids["case"] if index == 0 else open_case(
            conn,
            family_id=ids["family"],
            opened_by=ids["parent"],
            child_member_id=ids["member"],
            parent_text="",
            now=NOW,
        )
        apply_case(
            conn,
            case,
            "start",
            now=NOW + timedelta(seconds=index),
            rng=fixed_rng,
        )
        row = submit_digits(
            conn,
            case,
            "000000",
            now=NOW + timedelta(seconds=index, microseconds=1),
        )
        assert row["result"] == "wrong"
        assert row["events"][-1] == "code_did_not_match"
        assert row["static_locked"] is False
    assert load_case(conn, ids["case"], now=NOW)["static_locked"] is False


def test_right_static_code_then_unclear_digit_is_no_answer(conn):
    ids = seed(conn, app=False, push=False, static=True)
    apply_case(conn, ids["case"], "start", now=NOW)
    waiting = submit_digits(conn, ids["case"], STATIC_CODE, now=NOW + timedelta(seconds=1))
    assert waiting["state"] == "awaiting_answer"
    assert waiting["deadline_at"] == NOW + timedelta(seconds=1) + ANSWER_WINDOW
    assert waiting["events"] == ["start", "code_accepted"]
    assert STATIC_CODE not in case_text(conn, ids["case"])
    done = apply_case(
        conn, ids["case"], "answer_unclear", now=NOW + timedelta(seconds=2)
    )
    assert done["state"] == "not_confirmed"
    assert done["result"] == "no_answer"
    assert done["result"] != "not_sent"
    assert done["deadline_at"] is None


def test_keypad_yes_on_a_recent_number_is_yellow_and_a_no_is_red(conn):
    recent = seed(
        conn,
        app=False,
        push=False,
        static=True,
        phone_current_since=NOW - timedelta(hours=23),
        since_given=True,
    )
    _to_answer(conn, recent["case"], now=NOW)
    yellow = apply_case(conn, recent["case"], "answer_yes", now=NOW + timedelta(seconds=2))
    assert yellow["state"] == "not_confirmed"
    assert yellow["result"] == "number_recent"
    assert yellow["answered_via"] is None
    established = seed(conn, app=False, push=False, static=True)
    _to_answer(conn, established["case"], now=NOW)
    green = apply_case(
        conn, established["case"], "answer_yes", now=NOW + timedelta(seconds=2)
    )
    assert green["state"] == "confirmed"
    assert green["result"] == "sent"
    assert green["answered_via"] == "call"
    red = seed(
        conn,
        app=False,
        push=False,
        static=True,
        phone_current_since=NOW,
        since_given=True,
    )
    _to_answer(conn, red["case"], now=NOW)
    scam = apply_case(conn, red["case"], "answer_no", now=NOW + timedelta(seconds=2))
    assert scam["state"] == "scam"
    assert scam["result"] == "not_sent"
    assert scam["answered_via"] == "call"


def test_keypad_yes_at_exactly_24_hours_is_green(conn):
    ids = seed(
        conn,
        app=False,
        push=False,
        static=True,
        phone_current_since=NOW - NUMBER_RECENT_WINDOW,
        since_given=True,
    )
    _to_answer(conn, ids["case"], now=NOW)
    row = apply_case(conn, ids["case"], "answer_yes", now=NOW)
    assert row["number_recent"] is False
    assert row["state"] == "confirmed"
    assert row["result"] == "sent"


def test_push_yes_stays_green_when_the_number_is_new(conn):
    ids = seed(conn, app=True, push=True, phone_current_since=NOW, since_given=True)
    apply_case(conn, ids["case"], "start", now=NOW)
    row = apply_case(conn, ids["case"], "push_answered_yes", now=NOW)
    assert row["state"] == "confirmed"
    assert row["result"] == "sent"
    assert row["answered_via"] == "push"


def test_one_wrong_static_code_ends_the_case_and_a_second_guess_records_nothing(conn):
    ids = seed(conn, app=False, push=False, static=True)
    apply_case(conn, ids["case"], "start", now=NOW)
    done = submit_digits(conn, ids["case"], "9999", now=NOW + timedelta(seconds=1))
    assert done["state"] == "not_confirmed"
    assert done["result"] == "wrong"
    assert done["events"] == ["start", "static_code_mismatch"]
    updated_at = done["updated_at"]
    again = submit_digits(conn, ids["case"], STATIC_CODE, now=NOW + timedelta(seconds=2))
    assert again["result"] == "wrong"
    assert again["events"] == ["start", "static_code_mismatch"]
    assert again["updated_at"] == updated_at
    assert STATIC_CODE not in case_text(conn, ids["case"])


def test_empty_static_digits_record_nothing(conn):
    ids = seed(conn, app=False, push=False, static=True)
    started = apply_case(conn, ids["case"], "start", now=NOW)
    row = submit_digits(conn, ids["case"], "", now=NOW + timedelta(seconds=1))
    assert row["state"] == "calling"
    assert row["events"] == ["start"]
    assert row["updated_at"] == started["updated_at"]
    assert row["static_locked"] is False


def test_star_switches_to_the_static_code_once(conn):
    ids = seed(conn, app=True, push=False, static=True)
    apply_case(conn, ids["case"], "start", now=NOW, rng=fixed_rng)
    switched = submit_digits(conn, ids["case"], "*", now=NOW + timedelta(seconds=1))
    assert switched["state"] == "calling"
    assert switched["code_channel"] == "static"
    assert switched["events"] == ["start", "use_static_code"]
    assert switched["deadline_at"] == NOW + CODE_WINDOW
    assert switched["one_time_code_hash"] == hash_one_time(one_time_digits(ids["case"]))
    again = submit_digits(conn, ids["case"], "", now=NOW + timedelta(seconds=2))
    assert again["events"] == ["start", "use_static_code"]
    assert again["code_channel"] == "static"


def test_star_when_the_static_code_is_locked_does_not_ask_for_digits(conn):
    ids = seed(conn, app=True, push=False, static=True)
    _mismatch_until_locked(conn, ids)
    later = NOW + timedelta(minutes=1)
    case = open_case(
        conn,
        family_id=ids["family"],
        opened_by=ids["parent"],
        child_member_id=ids["member"],
        parent_text="",
        now=later,
    )
    apply_case(conn, case, "start", now=later, rng=fixed_rng)
    row = submit_digits(conn, case, "*", now=later + timedelta(seconds=1))
    assert row["state"] == "not_confirmed"
    assert row["result"] == "code_locked"
    assert row["events"][-1] == "use_static_code"
    assert "static_code_mismatch" not in row["events"]


def test_expired_one_time_code_hangs_up_yellow(conn, caplog):
    ids = seed(conn, app=True, push=False)
    issued = apply_case(conn, ids["case"], "start", now=NOW, rng=fixed_rng)
    code = one_time_digits(ids["case"])
    done = submit_digits(
        conn,
        ids["case"],
        code,
        now=issued["one_time_code_expires_at"],
    )
    assert done["result"] == "wrong"
    assert done["events"][-1] == "one_time_code_expired"
    assert done["one_time_code_used_at"] is None
    assert call_code(conn, ids["case"], now=issued["one_time_code_expires_at"]) is None
    assert code not in case_text(conn, ids["case"])
    assert code not in caplog.text


def test_a_used_one_time_code_is_rejected_when_the_case_is_still_calling(conn):
    ids = seed(conn, app=True, push=False)
    apply_case(conn, ids["case"], "start", now=NOW, rng=fixed_rng)
    conn.execute(
        "UPDATE cases SET one_time_code_used_at = %s WHERE id = %s",
        (NOW, ids["case"]),
    )
    code = one_time_digits(ids["case"])
    row = submit_digits(conn, ids["case"], code, now=NOW + timedelta(seconds=1))
    assert row["result"] == "wrong"
    assert row["events"][-1] == "code_did_not_match"
    assert call_code(conn, ids["case"], now=NOW + timedelta(seconds=1)) is None


def test_two_connections_derive_the_same_code(conn, database_url):
    ids = seed(conn, app=True, push=False)
    apply_case(conn, ids["case"], "start", now=NOW, rng=fixed_rng)
    code = one_time_digits(ids["case"])
    conn.commit()
    first = _connect(database_url)
    second = _connect(database_url)
    try:
        assert call_code(first, ids["case"], now=NOW) == code
        assert call_code(second, ids["case"], now=NOW) == code
        assert call_code(first, ids["case"], now=NOW) == call_code(second, ids["case"], now=NOW)
    finally:
        first.close()
        second.close()
        _delete_user_graph(database_url)


def test_reissue_replaces_the_nonce_and_kills_the_old_code(conn, caplog):
    ids = seed(conn, app=True, push=False)
    apply_case(conn, ids["case"], "start", now=NOW, rng=fixed_rng)
    old = one_time_digits(ids["case"])
    later = NOW + timedelta(seconds=30)
    row = reissue_one_time(conn, ids["case"], now=later, rng=lambda n: b"\x07" * n)
    new = derive_one_time(ids["case"], b"\x07" * 16)
    assert new != old
    assert bytes(row["one_time_nonce"]) == b"\x07" * 16
    assert row["one_time_code_hash"] == hash_one_time(new)
    assert row["one_time_code_expires_at"] == later + timedelta(minutes=5)
    assert row["one_time_code_used_at"] is None
    assert row["state"] == "calling"
    assert row["events"] == ["start"]
    assert call_code(conn, ids["case"], now=later) == new
    killed = submit_digits(conn, ids["case"], old, now=later + timedelta(seconds=1))
    assert killed["result"] == "wrong"
    assert killed["events"][-1] == "code_did_not_match"
    assert old not in case_text(conn, ids["case"])
    assert new not in case_text(conn, ids["case"])
    assert old not in caplog.text
    assert new not in caplog.text

    fresh = seed(conn, app=True, push=False)
    apply_case(conn, fresh["case"], "start", now=NOW, rng=fixed_rng)
    previous = one_time_digits(fresh["case"])
    reissue_one_time(
        conn, fresh["case"], now=later, rng=lambda n: b"\x09" * n
    )
    current = derive_one_time(fresh["case"], b"\x09" * 16)
    assert hash_one_time(previous) != load_case(conn, fresh["case"], now=later)["one_time_code_hash"]
    accepted = submit_digits(conn, fresh["case"], current, now=later + timedelta(seconds=1))
    assert accepted["state"] == "awaiting_answer"
    assert accepted["one_time_code_used_at"] == later + timedelta(seconds=1)
    assert call_code(conn, fresh["case"], now=later + timedelta(seconds=1)) is None


def test_reissue_is_refused_when_the_call_is_not_asking_for_a_one_time_code(conn):
    ids = seed(conn, app=False, push=False)
    apply_case(conn, ids["case"], "start", now=NOW, rng=fixed_rng)
    with pytest.raises(ValueError):
        reissue_one_time(conn, ids["case"], now=NOW, rng=fixed_rng)


def test_keypad_answer_before_the_code_records_nothing(conn):
    ids = seed(conn, app=False, push=False, static=True)
    started = apply_case(conn, ids["case"], "start", now=NOW)
    row = apply_case(conn, ids["case"], "answer_yes", now=NOW + timedelta(seconds=1))
    assert row["state"] == "calling"
    assert row["result"] is None
    assert row["events"] == ["start"]
    assert row["updated_at"] == started["updated_at"]


def test_unanswered_code_window_is_timeout_never_a_no(conn):
    ids = seed(conn, app=False, push=False)
    apply_case(conn, ids["case"], "start", now=NOW)
    apply_case(conn, ids["case"], "call_accepted", now=NOW + timedelta(seconds=1))
    row = apply_case(conn, ids["case"], "code_window_elapsed", now=NOW + CODE_WINDOW)
    assert row["state"] == "not_confirmed"
    assert row["result"] == "timeout"
    assert row["result"] != "not_sent"
    assert row["events"] == ["start", "code_window_elapsed"]


def test_first_slow_check_replays_and_the_second_times_out(conn):
    ids = seed(conn, app=True, push=False)
    apply_case(conn, ids["case"], "start", now=NOW, rng=fixed_rng)
    once = apply_case(conn, ids["case"], "code_check_slow", now=NOW + timedelta(seconds=1))
    assert once["state"] == "calling"
    assert once["result"] is None
    assert once["slow_checks"] == 1
    assert once["deadline_at"] == NOW + CODE_WINDOW
    assert once["events"] == ["start", "code_check_slow"]
    twice = apply_case(
        conn, ids["case"], "code_check_slow", now=NOW + timedelta(seconds=2)
    )
    assert twice["state"] == "not_confirmed"
    assert twice["result"] == "timeout"
    assert twice["slow_checks"] == 2
    assert twice["deadline_at"] is None
    assert twice["events"] == ["start", "code_check_slow", "code_check_slow"]
    columns_now, _ = columns(conn)
    assert "slow_checks" not in columns_now["cases"]


def test_push_yes_during_the_call_ignores_a_later_wrong_code(conn):
    ids = seed(conn, app=True, push=True)
    apply_case(conn, ids["case"], "start", now=NOW)
    apply_case(conn, ids["case"], "push_window_elapsed", now=NOW + PUSH_WINDOW, rng=fixed_rng)
    done = apply_case(
        conn, ids["case"], "push_answered_yes", now=NOW + PUSH_WINDOW + timedelta(seconds=1)
    )
    assert done["result"] == "sent"
    later = submit_digits(
        conn,
        ids["case"],
        "000000",
        now=NOW + PUSH_WINDOW + timedelta(seconds=2),
    )
    assert later["result"] == "sent"
    assert "code_did_not_match" not in later["events"]
    assert later["events"][-1] == "push_answered_yes"


def test_cancel_ends_any_open_case_as_timeout(conn):
    ids = seed(conn, app=True, push=True)
    apply_case(conn, ids["case"], "start", now=NOW)
    row = apply_case(conn, ids["case"], "cancel", now=NOW + timedelta(seconds=3))
    assert row["state"] == "not_confirmed"
    assert row["result"] == "timeout"
    assert row["deadline_at"] is None
    assert row["events"][-1] == "cancel"


def test_analysis_columns_survive_a_decision(conn):
    ids = seed(conn, app=True, push=True)
    conn.execute(
        """
        UPDATE cases
        SET transcript = %s, claims = %s::jsonb, pattern_id = 'tuition_or_school'
        WHERE id = %s
        """,
        ("send the tuition tonight", '{"story": "tuition"}', ids["case"]),
    )
    apply_case(conn, ids["case"], "start", now=NOW)
    done = apply_case(conn, ids["case"], "push_answered_no", now=NOW)
    assert done["result"] == "not_sent"
    assert done["transcript"] == "send the tuition tonight"
    assert done["claims"] == {"story": "tuition"}
    assert done["pattern_id"] == "tuition_or_school"


def test_replacing_a_check_code_requires_the_biometric_flag(conn):
    ids = seed(conn, app=True, static=True)
    with pytest.raises(Exception) as caught:
        set_check_code(
            conn,
            ids["member"],
            "2468",
            now=NOW,
            biometric_ok=False,
            rng=fixed_salt,
        )
    assert type(caught.value).__name__ == "BiometricRequired"
    assert "2468" not in str(caught.value)
    stored = conn.execute(
        "SELECT code_hash FROM family_members WHERE id = %s",
        (ids["member"],),
    ).fetchone()[0]
    assert stored.startswith("$argon2id$")
    assert stored != STATIC_CODE


def test_check_code_rejects_a_naive_clock_and_a_parent(conn):
    ids = seed(conn, app=False)
    with pytest.raises(ValueError):
        set_check_code(
            conn,
            ids["member"],
            STATIC_CODE,
            now=datetime(2026, 11, 3),
            biometric_ok=False,
            rng=fixed_salt,
        )
    parent = add_member(
        conn,
        family_id=ids["family"],
        role="parent",
        display_name="Parent",
        now=NOW,
        user_id=ids["parent"],
    )
    with pytest.raises(ValueError):
        set_check_code(
            conn,
            parent,
            STATIC_CODE,
            now=NOW,
            biometric_ok=False,
            rng=fixed_salt,
        )


def test_submit_digits_must_be_a_string(conn):
    ids = seed(conn, app=False, push=False, static=True)
    apply_case(conn, ids["case"], "start", now=NOW)
    with pytest.raises(TypeError):
        submit_digits(conn, ids["case"], None, now=NOW)
    row = load_case(conn, ids["case"], now=NOW)
    assert row["state"] == "calling"
    assert row["events"] == ["start"]


def test_apply_rejects_an_unknown_event_and_a_naive_clock(conn):
    ids = seed(conn)
    with pytest.raises(ValueError):
        apply_case(conn, ids["case"], "caller_id", now=NOW)
    assert load_case(conn, ids["case"], now=NOW)["state"] == "opened"
    with pytest.raises(ValueError):
        apply_case(conn, ids["case"], "start", now=datetime(2026, 11, 3))
    with pytest.raises(CaseNotFound):
        apply_case(conn, uuid4(), "start", now=NOW)


def test_apply_does_not_commit(database_url):
    setup = _connect(database_url)
    other = None
    try:
        ids = seed(setup, app=True, push=True)
        setup.commit()
        apply_case(setup, ids["case"], "start", now=NOW)
        other = _connect(database_url)
        visible = load_case(other, ids["case"], now=NOW)
        assert visible["state"] == "opened"
        assert visible["events"] == []
        setup.rollback()
        other.rollback()
        still = load_case(other, ids["case"], now=NOW)
        assert still["state"] == "opened"
        assert still["events"] == []
    finally:
        setup.rollback()
        setup.close()
        if other is not None:
            other.close()
        _delete_user_graph(database_url)


def test_apply_locks_the_case_row(database_url):
    setup = _connect(database_url)
    holder = None
    other = None
    try:
        ids = seed(setup, app=True, push=True)
        setup.commit()
        holder = _connect(database_url)
        holder.execute("SELECT id FROM cases WHERE id = %s FOR UPDATE", (ids["case"],))
        other = _connect(database_url)
        other.execute("SET statement_timeout = '750ms'")
        with pytest.raises(psycopg.errors.QueryCanceled):
            apply_case(other, ids["case"], "start", now=NOW)
    finally:
        if holder is not None:
            holder.rollback()
            holder.close()
        if other is not None:
            other.rollback()
            other.close()
        setup.rollback()
        setup.close()
        _delete_user_graph(database_url)


def test_complete_phone_otp_sets_opt_in_and_not_the_dial_clock(conn):
    ids = seed(conn, phone=False, established=False, status="invited", confirmed=False)
    number = next_phone()
    complete_phone_otp(conn, ids["member"], number, now=NOW, pending=False)
    row = conn.execute(
        """
        SELECT phone_e164, phone_opted_in_at, phone_current_since, pending_phone_e164
        FROM family_members WHERE id = %s
        """,
        (ids["member"],),
    ).fetchone()
    assert row[0] == number
    assert row[1] == NOW
    assert row[2] is None
    assert row[3] is None
    complete_phone_otp(conn, ids["member"], number, now=NOW + timedelta(minutes=1), pending=False)
    assert conn.execute(
        "SELECT phone_opted_in_at FROM family_members WHERE id = %s",
        (ids["member"],),
    ).fetchone()[0] == NOW


def test_otp_rejects_a_number_another_member_already_has(conn):
    first = seed(conn)
    second = seed(conn, phone=False, established=False, status="invited", confirmed=False)
    with pytest.raises(PhoneInUse) as caught:
        complete_phone_otp(conn, second["member"], first["phone"], now=NOW)
    assert first["phone"] not in str(caught.value)
    assert str(caught.value) == "phone_in_use"
    pending = next_phone()
    complete_phone_otp(conn, first["member"], pending, now=NOW, pending=True)
    third = seed(conn, phone=False, established=False, status="invited", confirmed=False)
    with pytest.raises(PhoneInUse):
        complete_phone_otp(conn, third["member"], pending, now=NOW)
    row = conn.execute(
        "SELECT phone_e164, pending_phone_e164 FROM family_members WHERE id = %s",
        (third["member"],),
    ).fetchone()
    assert row == (None, None)


def test_pending_otp_does_not_move_the_dial_target(conn):
    ids = seed(conn)
    replacement = next_phone("+82")
    complete_phone_otp(conn, ids["member"], replacement, now=NOW, pending=True)
    row = conn.execute(
        """
        SELECT phone_e164, phone_current_since, pending_phone_e164, pending_phone_set_at
        FROM family_members WHERE id = %s
        """,
        (ids["member"],),
    ).fetchone()
    assert row[0] == ids["phone"]
    assert row[1] == NOW - timedelta(days=2)
    assert row[2] == replacement
    assert row[3] == NOW
    with pytest.raises(ValueError):
        complete_phone_otp(conn, ids["member"], next_phone(), now=NOW, pending=False)


def test_otp_rejects_a_removed_member_and_a_bad_number(conn):
    ids = seed(conn, status="removed", confirmed=False)
    with pytest.raises(ValueError):
        complete_phone_otp(conn, ids["member"], next_phone(), now=NOW)
    invited = seed(conn, phone=False, established=False, status="invited", confirmed=False)
    with pytest.raises(ValueError):
        complete_phone_otp(conn, invited["member"], "+44 20", now=NOW)
    # +44 is a legal E.164 for the store. The API, not this layer, returns
    # unsupported_country.
    complete_phone_otp(conn, invited["member"], "+442079460000", now=NOW)
    stored = conn.execute(
        "SELECT phone_e164 FROM family_members WHERE id = %s",
        (invited["member"],),
    ).fetchone()[0]
    assert stored == "+442079460000"


def test_a_removed_members_number_can_be_claimed(conn):
    first = seed(conn)
    conn.execute(
        "UPDATE family_members SET status = 'removed' WHERE id = %s",
        (first["member"],),
    )
    second = seed(conn, phone=False, established=False, status="invited", confirmed=False)
    complete_phone_otp(conn, second["member"], first["phone"], now=NOW)
    assert conn.execute(
        "SELECT phone_e164 FROM family_members WHERE id = %s",
        (second["member"],),
    ).fetchone()[0] == first["phone"]


def test_open_case_rejects_a_child_from_another_family_and_a_parent(conn):
    first = seed(conn)
    second = seed(conn)
    with pytest.raises(ValueError):
        open_case(
            conn,
            family_id=second["family"],
            opened_by=second["parent"],
            child_member_id=first["member"],
            parent_text="",
            now=NOW,
        )
    parent = add_member(
        conn,
        family_id=first["family"],
        role="parent",
        display_name="Parent",
        now=NOW,
        user_id=first["parent"],
    )
    with pytest.raises(ValueError):
        open_case(
            conn,
            family_id=first["family"],
            opened_by=first["parent"],
            child_member_id=parent,
            parent_text="",
            now=NOW,
        )


def test_family_event_and_attempt_rows_round_trip(conn):
    ids = seed(conn)
    conn.execute(
        """
        INSERT INTO family_events (family_id, at, actor_user_id, step)
        VALUES (%s, %s, %s, 'child_confirmed')
        """,
        (ids["family"], NOW, ids["parent"]),
    )
    conn.execute(
        """
        INSERT INTO verification_attempts (
            case_id, channel, status, provider, provider_ref, started_at
        ) VALUES (%s, 'call', 'sent', 'twilio', 'CA123', %s)
        """,
        (ids["case"], NOW),
    )
    conn.execute(
        """
        INSERT INTO phone_otp (member_id, phone_e164, code_hash, expires_at, created_at)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (ids["member"], next_phone(), "a" * 64, NOW, NOW),
    )
    step = conn.execute(
        "SELECT step FROM family_events WHERE family_id = %s",
        (ids["family"],),
    ).fetchone()[0]
    assert step == "child_confirmed"


def _mismatch_until_locked(conn, ids):
    """Five static mismatches for this child.

    An app-linked child is asked for the one-time code first. Star switches
    that call to the static code, and the wrong four digits are what the
    lock counts. On a call that is already static, star changes nothing.
    """
    for index in range(5):
        case = ids["case"] if index == 0 else open_case(
            conn,
            family_id=ids["family"],
            opened_by=ids["parent"],
            child_member_id=ids["member"],
            parent_text="",
            now=NOW,
        )
        moment = NOW + timedelta(seconds=index)
        apply_case(conn, case, "start", now=moment, rng=fixed_rng)
        submit_digits(conn, case, "*", now=moment + timedelta(microseconds=1))
        submit_digits(conn, case, "0000", now=moment + timedelta(microseconds=2))


def _to_answer(conn, case_id, *, now):
    apply_case(conn, case_id, "start", now=now)
    waiting = submit_digits(conn, case_id, STATIC_CODE, now=now + timedelta(seconds=1))
    assert waiting["state"] == "awaiting_answer"


def _delete_user_graph(url: str) -> None:
    connection = _connect(url)
    try:
        connection.execute("DELETE FROM case_events")
        connection.execute("DELETE FROM verification_attempts")
        connection.execute("DELETE FROM cases")
        connection.execute("DELETE FROM family_events")
        connection.execute("DELETE FROM phone_otp")
        connection.execute("DELETE FROM family_members")
        connection.execute("DELETE FROM families")
        connection.execute("DELETE FROM sessions")
        connection.execute("DELETE FROM users")
        connection.commit()
    finally:
        connection.close()


def test_timeline_keeps_insertion_order_when_events_share_a_timestamp(conn):
    """Several events in one request share `now`. A random id must not reorder them."""
    for _ in range(20):
        ids = seed(conn, app=True)
        apply_case(conn, ids["case"], "start", now=NOW)
        apply_case(conn, ids["case"], "use_static_code", now=NOW)
        apply_case(conn, ids["case"], "code_check_slow", now=NOW)
        apply_case(conn, ids["case"], "code_accepted", now=NOW)
        apply_case(conn, ids["case"], "answer_no", now=NOW)
        view = load_case(conn, ids["case"], now=NOW)
        assert view["events"] == [
            "start",
            "use_static_code",
            "code_check_slow",
            "code_accepted",
            "answer_no",
        ]
