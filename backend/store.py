"""Postgres schema and the case transaction.

`apply_case` loads the case `FOR UPDATE`, copies `has_app`, `has_push_token`,
`has_opted_in_phone`, `number_recent`, and `static_locked` from the member,
calls `backend.verify.apply`, sets `deadline_at` from the state just entered,
and inserts one `case_events` row. The caller commits. A no-op, including a
second event after a terminal state, writes nothing.

`now` is the clock. `rng` is forwarded to `backend.codes` when a one-time
code or a static salt has to be chosen. This module does not call
`datetime.now` or `secrets`. The one-time plaintext sits in `memory` (the
process dict when the caller passes none). It is never a column.

See tests/test_store.py for the readings this file locks in.
"""

import re
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID

from psycopg import errors as pg_errors
from psycopg.rows import dict_row

from backend.codes import (
    OneTimeChallenge,
    StaticCode,
    issue_one_time,
    set_static_code,
    static_code_locked,
    submission_event,
)
from backend.verify import apply


SCHEMA_PATH = Path(__file__).with_name("schema.sql")
PUSH_WINDOW = timedelta(seconds=90)
CODE_WINDOW = timedelta(seconds=180)
ANSWER_WINDOW = timedelta(seconds=45)
NUMBER_RECENT_WINDOW = timedelta(hours=24)
_TERMINAL = frozenset({"confirmed", "scam", "not_confirmed"})
_DEADLINES = {
    "waiting_push": PUSH_WINDOW,
    "calling": CODE_WINDOW,
    "awaiting_answer": ANSWER_WINDOW,
}
_E164 = re.compile(r"^\+[1-9][0-9]{1,14}$")
_CALL_CODES: dict[str, dict] = {}

_CASE_SQL = """
    SELECT
        c.id, c.family_id, c.opened_by, c.child_member_id,
        c.state, c.result, c.answered_via, c.code_channel,
        c.parent_text, c.transcript, c.claims, c.pattern_id,
        c.one_time_code_hash, c.one_time_code_expires_at, c.one_time_code_used_at,
        c.deadline_at, c.audio_deleted_at, c.created_at, c.updated_at, c.decided_at,
        m.user_id, m.push_token, m.phone_e164, m.phone_opted_in_at,
        m.phone_current_since, m.code_set_at, m.code_hash, m.code_salt
    FROM cases AS c
    JOIN family_members AS m ON m.id = c.child_member_id
    WHERE c.id = %s
"""


class CaseNotFound(LookupError):
    """No case has this id."""


class PhoneInUse(Exception):
    """This E.164 is already a non-removed member's phone or pending phone."""


def clear_call_codes() -> None:
    """Drop every in-process one-time plaintext. A restart does this too."""
    _CALL_CODES.clear()


def apply_schema(conn) -> None:
    """Create the tables in the connection's current schema.

    Statements are executed one at a time so a literal `%` in a CHECK
    (the argon2id prefix) is not read as a placeholder. The file is still
    valid for `psql -f`.
    """
    with conn.cursor() as cur:
        for statement in _sql_statements(SCHEMA_PATH.read_text()):
            cur.execute(statement)


def _sql_statements(script: str) -> list[str]:
    statements = []
    current: list[str] = []
    for line in script.splitlines():
        if line.strip().startswith("--"):
            continue
        current.append(line)
        if line.strip().endswith(";"):
            statement = "\n".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
    tail = "\n".join(current).strip()
    if tail:
        statements.append(tail)
    return statements


def deadline_for(state: str, now: datetime) -> datetime | None:
    """Deadline for a state just entered. Terminal states and `opened` have none."""
    _require_aware(now, "now")
    window = _DEADLINES.get(state)
    if window is None:
        return None
    return now + window


def member_flags(member: dict, mismatch_ats, *, now: datetime) -> dict:
    """Flags `apply` reads, taken from the member and the mismatch timestamps.

    `number_recent` is true only while `phone_current_since` is strictly
    less than 24 hours before `now`. A blank push token is not a token.
    Opt-in requires both the number and `phone_opted_in_at`.
    """
    _require_aware(now, "now")
    since = member.get("phone_current_since")
    if since is not None:
        _require_aware(since, "phone_current_since")
    token = member.get("push_token")
    number = member.get("phone_e164")
    return {
        "has_app": member.get("user_id") is not None,
        "has_push_token": isinstance(token, str) and token.strip() != "",
        "has_opted_in_phone": (
            isinstance(number, str)
            and number != ""
            and member.get("phone_opted_in_at") is not None
        ),
        "number_recent": since is not None and (now - since) < NUMBER_RECENT_WINDOW,
        "static_locked": static_code_locked(
            mismatch_ats,
            code_set_at=member.get("code_set_at"),
            now=now,
        ),
    }


def create_user(
    conn,
    *,
    auth_provider: str,
    auth_subject: str,
    display_name: str,
    locale: str,
    now: datetime,
) -> UUID:
    _require_aware(now, "now")
    row = _one(
        conn,
        """
        INSERT INTO users (auth_provider, auth_subject, display_name, locale, created_at)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (auth_provider, auth_subject, display_name, locale, now),
    )
    return row["id"]


def create_family(conn, *, name: str, created_by: UUID, now: datetime) -> UUID:
    _require_aware(now, "now")
    row = _one(
        conn,
        """
        INSERT INTO families (name, created_by, created_at)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (name, created_by, now),
    )
    return row["id"]


def add_member(
    conn,
    *,
    family_id: UUID,
    role: str,
    display_name: str,
    now: datetime,
    user_id: UUID | None = None,
    status: str = "invited",
    phone_e164: str | None = None,
    phone_opted_in_at: datetime | None = None,
    phone_current_since: datetime | None = None,
    push_token: str | None = None,
    push_provider: str | None = None,
    push_env: str | None = None,
    confirmed_by_parent_at: datetime | None = None,
) -> UUID:
    """Insert one membership. A phone is rejected when another member has it.

    This is the row constructor the tests and later milestones build on. It
    is not the parent-confirm transition: `phone_current_since` is whatever
    the caller passes.
    """
    _require_aware(now, "now")
    if phone_e164 is not None:
        _require_e164(phone_e164)
        _assert_phone_available(conn, phone_e164, member_id=None, pending=False)
    row = _one(
        conn,
        """
        INSERT INTO family_members (
            family_id, user_id, role, display_name, status,
            phone_e164, phone_opted_in_at, phone_current_since,
            push_token, push_provider, push_env,
            confirmed_by_parent_at, created_at
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s
        )
        RETURNING id
        """,
        (
            family_id,
            user_id,
            role,
            display_name,
            status,
            phone_e164,
            phone_opted_in_at,
            phone_current_since,
            push_token,
            push_provider,
            push_env,
            confirmed_by_parent_at,
            now,
        ),
    )
    return row["id"]


def set_check_code(
    conn,
    member_id: UUID,
    code: str,
    *,
    now: datetime,
    biometric_ok: bool,
    rng=None,
) -> None:
    """Store a new argon2id hash and salt. The plaintext is not written."""
    member = _lock_member(conn, member_id)
    if member["role"] != "child":
        raise ValueError("check code is child only")
    stored = set_static_code(
        code,
        now=now,
        biometric_ok=biometric_ok,
        existing_set_at=member["code_set_at"],
        rng=rng,
    )
    _execute(
        conn,
        """
        UPDATE family_members
        SET code_hash = %s, code_salt = %s, code_set_at = %s
        WHERE id = %s
        """,
        (stored.code_hash, stored.salt, stored.code_set_at, member_id),
    )


def complete_phone_otp(
    conn,
    member_id: UUID,
    phone_e164: str,
    *,
    now: datetime,
    pending: bool = False,
) -> None:
    """Attach a number after OTP, or record a pending replacement.

    The first completion sets `phone_e164` and `phone_opted_in_at` and leaves
    `phone_current_since` null. `pending=True` writes only the pending
    columns. A number already held by a non-removed member raises PhoneInUse.
    Repeating the same write for this member changes nothing.
    """
    _require_aware(now, "now")
    _require_e164(phone_e164)
    if _assert_phone_available(conn, phone_e164, member_id=member_id, pending=pending):
        return
    member = _lock_member(conn, member_id)
    if member["status"] == "removed":
        raise ValueError("member_removed")
    if pending:
        if member["phone_e164"] is None:
            raise ValueError("no_current_phone")
        _execute(
            conn,
            """
            UPDATE family_members
            SET pending_phone_e164 = %s, pending_phone_set_at = %s
            WHERE id = %s
            """,
            (phone_e164, now, member_id),
        )
        return
    if member["phone_e164"] is not None:
        raise ValueError("phone_already_set")
    _execute(
        conn,
        """
        UPDATE family_members
        SET phone_e164 = %s, phone_opted_in_at = %s
        WHERE id = %s
        """,
        (phone_e164, now, member_id),
    )


def open_case(
    conn,
    *,
    family_id: UUID,
    opened_by: UUID,
    child_member_id: UUID,
    parent_text: str,
    now: datetime,
) -> UUID:
    _require_aware(now, "now")
    member = _lock_member(conn, child_member_id)
    if member["family_id"] != family_id:
        raise ValueError("child_not_in_family")
    if member["role"] != "child":
        raise ValueError("not_a_child")
    row = _one(
        conn,
        """
        INSERT INTO cases (
            family_id, opened_by, child_member_id, state, parent_text,
            created_at, updated_at
        ) VALUES (%s, %s, %s, 'opened', %s, %s, %s)
        RETURNING id
        """,
        (family_id, opened_by, child_member_id, parent_text, now, now),
    )
    return row["id"]


def load_case(conn, case_id: UUID, *, now: datetime) -> dict:
    _require_aware(now, "now")
    row = _load(conn, case_id, lock=False)
    if row is None:
        raise CaseNotFound(str(case_id))
    return _view(conn, row, now)


def apply_case(conn, case_id: UUID, event: str, *, now: datetime, rng=None, memory=None) -> dict:
    """Apply one state-machine event and persist it in this transaction."""
    _require_aware(now, "now")
    if not isinstance(event, str):
        raise TypeError("event must be a str")
    row = _load(conn, case_id, lock=True)
    if row is None:
        raise CaseNotFound(str(case_id))
    machine = _machine(conn, row, now)
    updated = apply(machine, event)
    if updated is machine:
        return _view(conn, row, now)
    _write_transition(
        conn,
        row,
        updated,
        now=now,
        step=event,
        rng=rng,
        memory=_memory(memory),
        used_at=row["one_time_code_used_at"],
    )
    fresh = _load(conn, case_id, lock=False)
    return _view(conn, fresh, now)


def submit_digits(conn, case_id: UUID, digits: str, *, now: datetime, memory=None) -> dict:
    """Turn keypad digits into one apply() event. Digits are not stored."""
    _require_aware(now, "now")
    if not isinstance(digits, str):
        raise TypeError("digits must be a str")
    row = _load(conn, case_id, lock=True)
    if row is None:
        raise CaseNotFound(str(case_id))
    machine = _machine(conn, row, now)
    decision = submission_event(
        machine,
        digits,
        now=now,
        static=_static(row),
        one_time=_one_time(row),
    )
    if decision.event is None:
        return _view(conn, row, now)
    updated = apply(machine, decision.event)
    if updated is machine:
        return _view(conn, row, now)
    mem = _memory(memory)
    used_at = row["one_time_code_used_at"]
    if decision.mark_one_time_used:
        used_at = now
        mem.pop(str(case_id), None)
    if decision.timeline_step == "one_time_code_expired":
        mem.pop(str(case_id), None)
    step = decision.timeline_step or decision.event
    _write_transition(
        conn,
        row,
        updated,
        now=now,
        step=step,
        rng=None,
        memory=mem,
        used_at=used_at,
    )
    fresh = _load(conn, case_id, lock=False)
    return _view(conn, fresh, now)


def call_code(case_id: UUID, *, now: datetime, memory=None) -> str | None:
    """Plaintext for this process, or None once it is used, expired, or gone."""
    _require_aware(now, "now")
    mem = _memory(memory)
    item = mem.get(str(case_id))
    if item is None:
        return None
    expires_at = item["expires_at"]
    _require_aware(expires_at, "expires_at")
    if now >= expires_at:
        mem.pop(str(case_id), None)
        return None
    return item["code"]


def _write_transition(
    conn,
    row: dict,
    updated: dict,
    *,
    now: datetime,
    step: str,
    rng,
    memory: dict,
    used_at,
) -> None:
    code_hash = row["one_time_code_hash"]
    expires_at = row["one_time_code_expires_at"]
    if (
        updated["state"] == "calling"
        and row["state"] != "calling"
        and updated.get("code_channel") == "one_time"
        and code_hash is None
    ):
        issued = issue_one_time(updated, now=now, rng=rng)
        if issued is not None:
            code_hash = issued.code_hash
            expires_at = issued.expires_at
            memory[str(row["id"])] = {
                "code": issued.code,
                "expires_at": issued.expires_at,
            }
    if updated["state"] != row["state"]:
        deadline = deadline_for(updated["state"], now)
        decided = now if updated["state"] in _TERMINAL else None
    else:
        deadline = row["deadline_at"]
        decided = row["decided_at"]
    _execute(
        conn,
        """
        UPDATE cases SET
            state = %s,
            result = %s,
            answered_via = %s,
            code_channel = %s,
            one_time_code_hash = %s,
            one_time_code_expires_at = %s,
            one_time_code_used_at = %s,
            deadline_at = %s,
            updated_at = %s,
            decided_at = %s
        WHERE id = %s
        """,
        (
            updated["state"],
            updated["result"],
            updated["answered_via"],
            updated["code_channel"],
            code_hash,
            expires_at,
            used_at,
            deadline,
            now,
            decided,
            row["id"],
        ),
    )
    _execute(
        conn,
        """
        INSERT INTO case_events (case_id, at, step)
        VALUES (%s, %s, %s)
        """,
        (row["id"], now, step),
    )


def _machine(conn, row: dict, now: datetime) -> dict:
    flags = member_flags(row, _mismatch_times(conn, row["child_member_id"]), now=now)
    return {
        "state": row["state"],
        "result": row["result"],
        "answered_via": row["answered_via"],
        "code_channel": row["code_channel"],
        "slow_checks": _slow_count(conn, row["id"]),
        **flags,
    }


def _view(conn, row: dict, now: datetime) -> dict:
    flags = member_flags(row, _mismatch_times(conn, row["child_member_id"]), now=now)
    return {
        "id": row["id"],
        "family_id": row["family_id"],
        "opened_by": row["opened_by"],
        "child_member_id": row["child_member_id"],
        "state": row["state"],
        "result": row["result"],
        "answered_via": row["answered_via"],
        "code_channel": row["code_channel"],
        "parent_text": row["parent_text"],
        "transcript": row["transcript"],
        "claims": row["claims"],
        "pattern_id": row["pattern_id"],
        "one_time_code_hash": row["one_time_code_hash"],
        "one_time_code_expires_at": row["one_time_code_expires_at"],
        "one_time_code_used_at": row["one_time_code_used_at"],
        "deadline_at": row["deadline_at"],
        "audio_deleted_at": row["audio_deleted_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "decided_at": row["decided_at"],
        "slow_checks": _slow_count(conn, row["id"]),
        "events": _steps(conn, row["id"]),
        **flags,
    }


def _static(row: dict) -> StaticCode | None:
    if row["code_hash"] is None or row["code_salt"] is None or row["code_set_at"] is None:
        return None
    salt = row["code_salt"]
    if not isinstance(salt, bytes):
        salt = bytes(salt)
    return StaticCode(row["code_hash"], salt, row["code_set_at"])


def _one_time(row: dict) -> OneTimeChallenge | None:
    if row["one_time_code_hash"] is None:
        return None
    return OneTimeChallenge(
        row["one_time_code_hash"],
        row["one_time_code_expires_at"],
        row["one_time_code_used_at"],
    )


def _assert_phone_available(conn, phone_e164: str, *, member_id: UUID | None, pending: bool) -> bool:
    """True when this member already holds the number in the target column."""
    _execute(conn, "SELECT pg_advisory_xact_lock(hashtext(%s)::bigint)", (phone_e164,))
    if member_id is None:
        rows = _all(
            conn,
            """
            SELECT id, phone_e164, pending_phone_e164
            FROM family_members
            WHERE status <> 'removed'
              AND (phone_e164 = %s OR pending_phone_e164 = %s)
            ORDER BY id
            FOR UPDATE
            """,
            (phone_e164, phone_e164),
        )
    else:
        rows = _all(
            conn,
            """
            SELECT id, status, phone_e164, pending_phone_e164
            FROM family_members
            WHERE id = %s
               OR (
                    status <> 'removed'
                    AND (phone_e164 = %s OR pending_phone_e164 = %s)
               )
            ORDER BY id
            FOR UPDATE
            """,
            (member_id, phone_e164, phone_e164),
        )
        if not any(row["id"] == member_id for row in rows):
            raise CaseNotFound(str(member_id))
        member = next(row for row in rows if row["id"] == member_id)
        if member["status"] == "removed":
            raise ValueError("member_removed")
    for row in rows:
        owns_phone = row["phone_e164"] == phone_e164
        owns_pending = row["pending_phone_e164"] == phone_e164
        if member_id is not None and row["id"] == member_id:
            if pending and owns_pending:
                return True
            if not pending and owns_phone:
                return True
            if owns_phone or owns_pending:
                raise PhoneInUse("phone_in_use")
            continue
        if owns_phone or owns_pending:
            raise PhoneInUse("phone_in_use")
    return False


def _lock_member(conn, member_id: UUID) -> dict:
    row = _one(
        conn,
        """
        SELECT id, family_id, role, status, phone_e164, code_set_at
        FROM family_members
        WHERE id = %s
        FOR UPDATE
        """,
        (member_id,),
    )
    if row is None:
        raise CaseNotFound(str(member_id))
    return row


def _load(conn, case_id: UUID, *, lock: bool) -> dict | None:
    sql = _CASE_SQL
    if lock:
        sql += " FOR UPDATE OF c, m"
    return _one(conn, sql, (case_id,))


def _mismatch_times(conn, member_id: UUID) -> list[datetime]:
    rows = _all(
        conn,
        """
        SELECT e.at
        FROM case_events AS e
        JOIN cases AS c ON c.id = e.case_id
        WHERE c.child_member_id = %s
          AND e.step = 'static_code_mismatch'
        """,
        (member_id,),
    )
    return [row["at"] for row in rows]


def _slow_count(conn, case_id: UUID) -> int:
    row = _one(
        conn,
        """
        SELECT count(*) AS n
        FROM case_events
        WHERE case_id = %s AND step = 'code_check_slow'
        """,
        (case_id,),
    )
    return int(row["n"])


def _steps(conn, case_id: UUID) -> list[str]:
    rows = _all(
        conn,
        """
        SELECT step
        FROM case_events
        WHERE case_id = %s
        ORDER BY at ASC, id ASC
        """,
        (case_id,),
    )
    return [row["step"] for row in rows]


def _memory(memory: dict | None) -> dict:
    return _CALL_CODES if memory is None else memory


def _require_e164(value: str) -> str:
    if not isinstance(value, str) or _E164.fullmatch(value) is None:
        raise ValueError("invalid_phone")
    return value


def _require_aware(value: object, label: str) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.tzinfo.utcoffset(value) is None
    ):
        raise ValueError(f"{label} must be a timezone-aware datetime")
    return value


def _one(conn, sql: str, params: tuple):
    with _phone_errors():
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def _all(conn, sql: str, params: tuple) -> list:
    with _phone_errors():
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def _execute(conn, sql: str, params: tuple = ()) -> None:
    with _phone_errors():
        with conn.cursor() as cur:
            cur.execute(sql, params)


def _phone_errors():
    """Hide an E.164 that a unique-index race would otherwise put in the error."""
    return _PhoneErrorGuard()


class _PhoneErrorGuard:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, _tb):
        if exc_type is None or not issubclass(exc_type, pg_errors.UniqueViolation):
            return False
        name = exc.diag.constraint_name or ""
        if "phone" not in name:
            return False
        raise PhoneInUse("phone_in_use") from None
