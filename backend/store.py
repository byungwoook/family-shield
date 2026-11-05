"""Postgres schema and the case transaction.

`apply_case` loads the case `FOR UPDATE`, copies `has_app`, `has_push_token`,
`has_opted_in_phone`, `number_recent`, and `static_locked` from the member,
calls `backend.verify.apply`, sets `deadline_at` from the state just entered,
and inserts one `case_events` row. The caller commits. A no-op, including a
second event after a terminal state, writes nothing.

`now` is the clock. `rng` is forwarded to `backend.codes` when a one-time
code or a static salt has to be chosen. This module does not call
`datetime.now` or `secrets`. A one-time code is not kept. The row stores a
nonce, and `call_code` derives the digits from that nonce.

Session rows, the dev helper that marks a child callable, and one call
attempt row are written here too. Milestone 5 adds invites, SMS OTP
challenges, parent confirm and reject, and family timeline rows. None of
them commit.

See tests/test_store.py for the readings this file locks in.
"""

import re
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID

from psycopg import errors as pg_errors
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from backend.codes import (
    OneTimeChallenge,
    StaticCode,
    derive_one_time,
    generate_one_time,
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
_CASE_SQL = """
    SELECT
        c.id, c.family_id, c.opened_by, c.child_member_id,
        c.state, c.result, c.answered_via,         c.code_channel,
        c.parent_text, c.transcript, c.claims, c.pattern_id,
        c.one_time_nonce, c.one_time_code_hash,
        c.one_time_code_expires_at, c.one_time_code_used_at,
        c.deadline_at, c.audio_deleted_at, c.created_at, c.updated_at, c.decided_at,
        m.user_id, m.push_token, m.phone_e164, m.phone_opted_in_at,
        m.phone_current_since, m.code_set_at, m.code_hash, m.code_salt
    FROM cases AS c
    JOIN family_members AS m ON m.id = c.child_member_id
    WHERE c.id = %s
"""


class CaseNotFound(LookupError):
    """No case has this id."""


class RateLimited(Exception):
    """A per-member cap was reached. Nothing was written."""


class PhoneInUse(Exception):
    """This E.164 is already a non-removed member's phone or pending phone."""


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


def apply_case(
    conn,
    case_id: UUID,
    event: str,
    *,
    now: datetime,
    rng=None,
    step: str | None = None,
) -> dict:
    """Apply one state-machine event and persist it in this transaction.

    The timeline row is `step` when given, else the event name.
    """
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
        step=step or event,
        rng=rng,
        used_at=row["one_time_code_used_at"],
    )
    fresh = _load(conn, case_id, lock=False)
    return _view(conn, fresh, now)


def submit_digits(conn, case_id: UUID, digits: str, *, now: datetime) -> dict:
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
    used_at = row["one_time_code_used_at"]
    if decision.mark_one_time_used:
        used_at = now
    step = decision.timeline_step or decision.event
    _write_transition(
        conn,
        row,
        updated,
        now=now,
        step=step,
        rng=None,
        used_at=used_at,
    )
    fresh = _load(conn, case_id, lock=False)
    return _view(conn, fresh, now)


def reissue_one_time(conn, case_id: UUID, *, now: datetime, rng=None) -> dict:
    """Replace the nonce. The previous digits no longer match the stored hash.

    Legal only while this case is `calling` on the one-time channel and a
    nonce is already stored. Expiry starts again at `now`. `used_at` is cleared.
    """
    _require_aware(now, "now")
    row = _load(conn, case_id, lock=True)
    if row is None:
        raise CaseNotFound(str(case_id))
    if row["state"] != "calling" or row["code_channel"] != "one_time":
        raise ValueError("one_time_not_active")
    if row["one_time_nonce"] is None:
        raise ValueError("one_time_not_issued")
    issued = generate_one_time(case_id=case_id, now=now, rng=rng)
    _execute(
        conn,
        """
        UPDATE cases SET
            one_time_nonce = %s,
            one_time_code_hash = %s,
            one_time_code_expires_at = %s,
            one_time_code_used_at = NULL,
            updated_at = %s
        WHERE id = %s
        """,
        (issued.nonce, issued.code_hash, issued.expires_at, now, case_id),
    )
    fresh = _load(conn, case_id, lock=False)
    return _view(conn, fresh, now)


def ensure_user(
    conn,
    *,
    auth_provider: str,
    auth_subject: str,
    display_name: str,
    locale: str,
    now: datetime,
) -> UUID:
    """Return the user for this subject, creating one when it is new.

    A concurrent insert rolls back to a savepoint and reads the winner.
    Display name and locale stay as they were on the first insert.
    """
    _require_aware(now, "now")
    existing = _user_id(conn, auth_provider, auth_subject)
    if existing is not None:
        return existing
    try:
        with conn.transaction():
            return create_user(
                conn,
                auth_provider=auth_provider,
                auth_subject=auth_subject,
                display_name=display_name,
                locale=locale,
                now=now,
            )
    except pg_errors.UniqueViolation:
        found = _user_id(conn, auth_provider, auth_subject)
        if found is None:
            raise
        return found


def create_session(
    conn,
    *,
    user_id: UUID,
    token_hash: str,
    expires_at: datetime,
) -> UUID:
    """Store the hash of a session token. The plaintext is not a parameter."""
    _require_aware(expires_at, "expires_at")
    if not isinstance(token_hash, str) or len(token_hash) < 32 or token_hash.strip() == "":
        raise ValueError("token_hash_too_short")
    row = _one(
        conn,
        """
        INSERT INTO sessions (user_id, token_hash, expires_at)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (user_id, token_hash, expires_at),
    )
    return row["id"]


def session_user(conn, token_hash: str, *, now: datetime) -> dict | None:
    """The user behind this hash, or None when it is missing, expired, or revoked.

    Expiry is `now >= expires_at`. A missing row and a dead row look the same.
    """
    _require_aware(now, "now")
    if not isinstance(token_hash, str):
        return None
    row = _one(
        conn,
        """
        SELECT s.user_id, s.expires_at, s.revoked_at, u.display_name, u.locale
        FROM sessions AS s
        JOIN users AS u ON u.id = s.user_id
        WHERE s.token_hash = %s
        """,
        (token_hash,),
    )
    if row is None or row["revoked_at"] is not None or now >= row["expires_at"]:
        return None
    return {
        "user_id": row["user_id"],
        "display_name": row["display_name"],
        "locale": row["locale"],
    }


def memberships_for_user(conn, user_id: UUID) -> list:
    """Non-removed memberships for this user."""
    return _all(
        conn,
        """
        SELECT id, family_id, role, status
        FROM family_members
        WHERE user_id = %s AND status <> 'removed'
        ORDER BY created_at ASC, id ASC
        """,
        (user_id,),
    )


def member_contact(conn, member_id: UUID) -> dict | None:
    """The membership columns the API needs to authorize a request.

    No code hash, salt, or nonce.
    """
    return _one(
        conn,
        """
        SELECT
            id, family_id, user_id, role, display_name, status,
            phone_e164, phone_opted_in_at, phone_current_since,
            confirmed_by_parent_at, push_token
        FROM family_members
        WHERE id = %s
        """,
        (member_id,),
    )


def active_parent(conn, user_id: UUID, family_id: UUID) -> dict | None:
    row = _one(
        conn,
        """
        SELECT id
        FROM family_members
        WHERE user_id = %s AND family_id = %s
          AND role = 'parent' AND status = 'active'
        """,
        (user_id, family_id),
    )
    return row


def mark_member_callable(
    conn,
    member_id: UUID,
    phone_e164: str,
    *,
    now: datetime,
    user_id: UUID | None = None,
) -> None:
    """Mark an invited child active with an opted-in number. No SMS is sent.

    The first completion sets `phone_opted_in_at`, `phone_current_since`,
    and `confirmed_by_parent_at` to `now`. Repeating it for the same number
    does not move those clocks. A different number is refused. `user_id`,
    when passed, links the child account; a user who already belongs to a
    family cannot be linked.
    """
    _require_aware(now, "now")
    _require_e164(phone_e164)
    member = _lock_member(conn, member_id)
    if member["role"] != "child":
        raise ValueError("not_a_child")
    if member["status"] == "removed":
        raise ValueError("member_removed")
    if user_id is not None:
        _bind_child_user(conn, member_id, user_id)
    if member["phone_e164"] is None:
        complete_phone_otp(conn, member_id, phone_e164, now=now, pending=False)
    elif member["phone_e164"] != phone_e164:
        raise ValueError("phone_already_set")
    _execute(
        conn,
        """
        UPDATE family_members
        SET status = 'active',
            phone_current_since = COALESCE(phone_current_since, %s),
            confirmed_by_parent_at = COALESCE(confirmed_by_parent_at, %s),
            user_id = COALESCE(%s, user_id)
        WHERE id = %s
        """,
        (now, now, user_id, member_id),
    )


def lock_case(conn, case_id: UUID, *, now: datetime) -> dict:
    """The case view with the row locked. The caller commits."""
    _require_aware(now, "now")
    row = _load(conn, case_id, lock=True)
    if row is None:
        raise CaseNotFound(str(case_id))
    return _view(conn, row, now)


def record_call_attempt(conn, case_id: UUID, *, now: datetime) -> UUID:
    """One call attempt, written as `sending` before anything is dialed.

    `finish_call_attempt` moves it to `sent` with the CallSid once the
    provider accepts, or to `failed` when it does not.
    """
    _require_aware(now, "now")
    row = _one(
        conn,
        """
        INSERT INTO verification_attempts (
            case_id, channel, status, provider, started_at
        ) VALUES (%s, 'call', 'sending', 'twilio', %s)
        RETURNING id
        """,
        (case_id, now),
    )
    return row["id"]


def finish_attempt(
    conn,
    attempt_id: UUID,
    *,
    status: str,
    now: datetime,
    provider_ref: str | None = None,
) -> None:
    """`sent` with the provider's reference (a CallSid), or `failed` with an end time."""
    _require_aware(now, "now")
    if status not in ("sent", "failed"):
        raise ValueError("attempt status must be sent or failed")
    _execute(
        conn,
        """
        UPDATE verification_attempts
        SET status = %s,
            provider_ref = COALESCE(%s, provider_ref),
            ended_at = CASE WHEN %s = 'failed' THEN %s ELSE ended_at END
        WHERE id = %s
        """,
        (status, provider_ref, status, now, attempt_id),
    )


finish_call_attempt = finish_attempt


def call_attempt(conn, case_id: UUID, call_sid: str) -> dict | None:
    """The call attempt on this case with this CallSid, locked. None when it is not ours."""
    if not isinstance(call_sid, str) or call_sid == "":
        return None
    return _one(
        conn,
        """
        SELECT id, status, ended_at
        FROM verification_attempts
        WHERE case_id = %s AND channel = 'call' AND provider_ref = %s
        FOR UPDATE
        """,
        (case_id, call_sid),
    )


def end_call_attempt(conn, attempt_id: UUID, *, failed: bool, now: datetime) -> None:
    """Record the end of the call. The first end time wins."""
    _require_aware(now, "now")
    _execute(
        conn,
        """
        UPDATE verification_attempts
        SET status = CASE WHEN %s THEN 'failed' ELSE status END,
            ended_at = COALESCE(ended_at, %s)
        WHERE id = %s
        """,
        (failed, now, attempt_id),
    )


def issue_invite(
    conn,
    member_id: UUID,
    *,
    invite_hash: str,
    expires_at: datetime,
) -> None:
    """Store a new invite hash for an invited child nobody has claimed yet.

    A second issue replaces the first, so an older secret stops working.
    """
    _require_aware(expires_at, "expires_at")
    if not isinstance(invite_hash, str) or len(invite_hash) < 32:
        raise ValueError("token_hash_too_short")
    member = _one(
        conn,
        """
        SELECT role, status, user_id
        FROM family_members
        WHERE id = %s
        FOR UPDATE
        """,
        (member_id,),
    )
    if member is None:
        raise CaseNotFound(str(member_id))
    if (
        member["role"] != "child"
        or member["status"] != "invited"
        or member["user_id"] is not None
    ):
        raise ValueError("invite_not_open")
    _execute(
        conn,
        """
        UPDATE family_members
        SET invite_hash = %s, invite_expires_at = %s
        WHERE id = %s
        """,
        (invite_hash, expires_at, member_id),
    )


def accept_invite(conn, *, invite_hash: str, user_id: UUID, now: datetime) -> dict:
    """Link this user to the invited child row and burn the secret.

    An unknown, used, or replaced secret is `invite_invalid`. A live row
    past `invite_expires_at` is `invite_expired` and keeps its hash, so the
    answer stays the same until the parent issues a new one. A user who
    already holds a non-removed membership anywhere cannot accept.
    """
    _require_aware(now, "now")
    row = _one(
        conn,
        """
        SELECT id, family_id, role, status, user_id, display_name, invite_expires_at
        FROM family_members
        WHERE invite_hash = %s
        FOR UPDATE
        """,
        (invite_hash,),
    )
    if (
        row is None
        or row["role"] != "child"
        or row["status"] != "invited"
        or row["user_id"] is not None
    ):
        raise ValueError("invite_invalid")
    if now >= row["invite_expires_at"]:
        raise ValueError("invite_expired")
    _bind_child_user(conn, row["id"], user_id)
    _execute(
        conn,
        """
        UPDATE family_members
        SET user_id = %s, invite_hash = NULL, invite_expires_at = NULL
        WHERE id = %s
        """,
        (user_id, row["id"]),
    )
    add_family_event(
        conn, row["family_id"], now=now, actor_user_id=user_id, step="invite_accepted"
    )
    return {
        "id": row["id"],
        "family_id": row["family_id"],
        "display_name": row["display_name"],
    }


def child_membership(conn, user_id: UUID) -> dict | None:
    """This user's one non-removed child row, with the columns enrollment reads."""
    rows = _all(
        conn,
        """
        SELECT id, family_id, status, phone_e164, phone_opted_in_at,
               confirmed_by_parent_at
        FROM family_members
        WHERE user_id = %s AND role = 'child' AND status <> 'removed'
        ORDER BY created_at ASC, id ASC
        """,
        (user_id,),
    )
    if len(rows) != 1:
        return None
    return rows[0]


def start_phone_otp(
    conn,
    member_id: UUID,
    phone_e164: str,
    *,
    code_hash: str,
    now: datetime,
    expires_at: datetime,
    daily_limit: int,
) -> None:
    """Write one challenge and consume this member's older live ones.

    The member row is locked first so two starts cannot both pass the cap.
    The cap counts every challenge created in the last 24 hours, including
    consumed ones. At the cap this raises RateLimited and writes nothing.
    """
    _require_aware(now, "now")
    _require_aware(expires_at, "expires_at")
    _require_e164(phone_e164)
    _lock_member(conn, member_id)
    row = _one(
        conn,
        """
        SELECT count(*) AS n
        FROM phone_otp
        WHERE member_id = %s AND created_at > %s
        """,
        (member_id, now - timedelta(hours=24)),
    )
    if row["n"] >= daily_limit:
        raise RateLimited("rate_limited")
    _execute(
        conn,
        """
        UPDATE phone_otp
        SET consumed_at = %s
        WHERE member_id = %s AND consumed_at IS NULL
        """,
        (now, member_id),
    )
    _execute(
        conn,
        """
        INSERT INTO phone_otp (
            member_id, phone_e164, code_hash, expires_at, attempts, created_at
        ) VALUES (%s, %s, %s, %s, 0, %s)
        """,
        (member_id, phone_e164, code_hash, expires_at, now),
    )


def check_phone_otp(
    conn,
    member_id: UUID,
    phone_e164: str,
    *,
    matches,
    now: datetime,
    max_attempts: int,
) -> str:
    """`ok`, `wrong`, or `dead`. The caller commits on every outcome.

    `matches(stored_hash) -> bool` is the comparison, so this module never
    sees the digits. Only the newest live challenge for this member and
    this number counts. A miss increments `attempts`; the miss that reaches
    `max_attempts` also consumes the challenge, so the right code after that
    is `dead`. Expired, consumed, or missing is `dead` too.
    """
    _require_aware(now, "now")
    row = _one(
        conn,
        """
        SELECT id, code_hash, expires_at, attempts
        FROM phone_otp
        WHERE member_id = %s AND phone_e164 = %s AND consumed_at IS NULL
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        FOR UPDATE
        """,
        (member_id, phone_e164),
    )
    if row is None or now >= row["expires_at"] or row["attempts"] >= max_attempts:
        return "dead"
    if matches(row["code_hash"]):
        _execute(
            conn,
            "UPDATE phone_otp SET consumed_at = %s WHERE id = %s",
            (now, row["id"]),
        )
        return "ok"
    attempts = row["attempts"] + 1
    _execute(
        conn,
        """
        UPDATE phone_otp
        SET attempts = %s,
            consumed_at = CASE WHEN %s >= %s THEN %s ELSE consumed_at END
        WHERE id = %s
        """,
        (attempts, attempts, max_attempts, now, row["id"]),
    )
    return "wrong"


def confirm_member(conn, member_id: UUID, *, now: datetime, actor_user_id: UUID) -> dict:
    """Parent confirm: the child becomes callable and the 24-hour clock starts.

    Allowed only for an invited child that accepted the invite and proved a
    number with OTP. Anything else is `member_not_ready`.
    """
    _require_aware(now, "now")
    member = _lock_pending_child(conn, member_id)
    if member["user_id"] is None or member["phone_opted_in_at"] is None:
        raise ValueError("member_not_ready")
    _execute(
        conn,
        """
        UPDATE family_members
        SET status = 'active',
            confirmed_by_parent_at = %s,
            phone_current_since = %s
        WHERE id = %s
        """,
        (now, now, member_id),
    )
    add_family_event(
        conn, member["family_id"], now=now, actor_user_id=actor_user_id, step="child_confirmed"
    )
    return member_contact(conn, member_id)


def reject_member(conn, member_id: UUID, *, now: datetime, actor_user_id: UUID) -> None:
    """Parent reject: the row is removed and its invite and number are freed."""
    _require_aware(now, "now")
    member = _lock_pending_child(conn, member_id)
    _execute(
        conn,
        """
        UPDATE family_members
        SET status = 'removed', invite_hash = NULL, invite_expires_at = NULL
        WHERE id = %s
        """,
        (member_id,),
    )
    add_family_event(
        conn, member["family_id"], now=now, actor_user_id=actor_user_id, step="child_rejected"
    )


def family_roster(conn, family_id: UUID) -> list:
    """Non-removed members for the parent screen. No hashes and no full number."""
    rows = _all(
        conn,
        """
        SELECT id, role, display_name, status, user_id, phone_e164,
               phone_opted_in_at, confirmed_by_parent_at, code_set_at,
               invite_expires_at
        FROM family_members
        WHERE family_id = %s AND status <> 'removed'
        ORDER BY created_at ASC, id ASC
        """,
        (family_id,),
    )
    out = []
    for row in rows:
        phone = row["phone_e164"]
        out.append(
            {
                "id": row["id"],
                "role": row["role"],
                "display_name": row["display_name"],
                "status": row["status"],
                "linked": row["user_id"] is not None,
                "phone_last4": phone[-4:] if isinstance(phone, str) else None,
                "phone_verified": row["phone_opted_in_at"] is not None,
                "has_check_code": row["code_set_at"] is not None,
                "awaiting_confirm": (
                    row["role"] == "child"
                    and row["status"] == "invited"
                    and row["user_id"] is not None
                    and row["phone_opted_in_at"] is not None
                ),
                "invite_expires_at": row["invite_expires_at"],
                "confirmed_at": row["confirmed_by_parent_at"],
            }
        )
    return out


def add_family_event(
    conn,
    family_id: UUID,
    *,
    now: datetime,
    actor_user_id: UUID | None,
    step: str,
) -> None:
    """One family timeline row. The step is an id, never a code or a number."""
    _require_aware(now, "now")
    _execute(
        conn,
        """
        INSERT INTO family_events (family_id, at, actor_user_id, step)
        VALUES (%s, %s, %s, %s)
        """,
        (family_id, now, actor_user_id, step),
    )


_TIMED_EVENTS = {
    "waiting_push": ("push_window_elapsed", "push_window_elapsed"),
    "calling": ("code_window_elapsed", "code_window_elapsed"),
    "awaiting_answer": ("answer_window_elapsed", "answer_window_elapsed"),
}


def set_push_token(
    conn,
    member_id: UUID,
    *,
    user_id: UUID,
    provider: str,
    token: str,
    env: str | None,
    locale: str,
) -> None:
    """Store this device's token on the child's row and the device locale on the user.

    One token is one device: if another membership held it, that row loses it.
    """
    _execute(
        conn,
        """
        UPDATE family_members
        SET push_token = NULL, push_provider = NULL, push_env = NULL
        WHERE push_token = %s AND id <> %s
        """,
        (token, member_id),
    )
    _execute(
        conn,
        """
        UPDATE family_members
        SET push_token = %s, push_provider = %s, push_env = %s
        WHERE id = %s
        """,
        (token, provider, env, member_id),
    )
    _execute(conn, "UPDATE users SET locale = %s WHERE id = %s", (locale, user_id))


def clear_push_token(conn, member_id: UUID, token: str) -> None:
    """Forget a token the provider called dead, unless the device already sent a new one."""
    _execute(
        conn,
        """
        UPDATE family_members
        SET push_token = NULL, push_provider = NULL, push_env = NULL
        WHERE id = %s AND push_token = %s
        """,
        (member_id, token),
    )


def push_target(conn, member_id: UUID) -> dict | None:
    """Provider, token, env, and the child's locale. None when there is no token."""
    row = _one(
        conn,
        """
        SELECT m.push_provider, m.push_token, m.push_env, u.locale
        FROM family_members AS m
        LEFT JOIN users AS u ON u.id = m.user_id
        WHERE m.id = %s
        """,
        (member_id,),
    )
    if row is None or not row["push_token"]:
        return None
    return {
        "provider": row["push_provider"],
        "token": row["push_token"],
        "env": row["push_env"],
        "locale": row["locale"] or "en",
    }


def record_push_attempt(conn, case_id: UUID, *, provider: str, now: datetime) -> UUID:
    """One push attempt, `sending` until the provider answers."""
    _require_aware(now, "now")
    row = _one(
        conn,
        """
        INSERT INTO verification_attempts (case_id, channel, status, provider, started_at)
        VALUES (%s, 'push', 'sending', %s, %s)
        RETURNING id
        """,
        (case_id, provider, now),
    )
    return row["id"]


def supersede_push_attempts(conn, case_id: UUID, *, now: datetime) -> None:
    """The window passed and the call takes over: open push attempts are superseded."""
    _execute(
        conn,
        """
        UPDATE verification_attempts
        SET status = 'superseded', ended_at = COALESCE(ended_at, %s)
        WHERE case_id = %s AND channel = 'push' AND status IN ('sending', 'sent')
        """,
        (now, case_id),
    )


def due_case_ids(conn, *, now: datetime, limit: int = 100) -> list:
    """Open cases whose deadline has passed, oldest deadline first."""
    _require_aware(now, "now")
    rows = _all(
        conn,
        """
        SELECT id
        FROM cases
        WHERE state IN ('waiting_push', 'calling', 'awaiting_answer')
          AND deadline_at IS NOT NULL
          AND deadline_at <= %s
        ORDER BY deadline_at ASC, id ASC
        LIMIT %s
        """,
        (now, limit),
    )
    return [row["id"] for row in rows]


def expire_case(conn, case_id: UUID, *, now: datetime, rng=None) -> dict | None:
    """Apply this case's window event if its deadline has passed. None when nothing moved.

    The case is locked first and the deadline read again, so a webhook or an
    answer that won the race leaves nothing for the timer to do.
    """
    _require_aware(now, "now")
    row = _load(conn, case_id, lock=True)
    if row is None or row["state"] not in _TIMED_EVENTS:
        return None
    deadline = row["deadline_at"]
    if deadline is None or deadline > now:
        return None
    event, step = _TIMED_EVENTS[row["state"]]
    view = apply_case(conn, case_id, event, now=now, rng=rng, step=step)
    return view if view["state"] != row["state"] else None


TEXT_RETENTION = timedelta(days=30)


def save_analysis(
    conn,
    case_id: UUID,
    *,
    now: datetime,
    transcript: str | None = None,
    claims: dict | None = None,
    pattern_id: str | None = None,
    audio_deleted: bool = False,
) -> None:
    """Store what the voice note said. Never touches state, result, or the timeline.

    Writes only the columns passed as non-None. `audio_deleted` stamps
    `audio_deleted_at` (the first stamp wins). A case already past the text
    retention window keeps its text deleted.
    """
    _require_aware(now, "now")
    _execute(
        conn,
        """
        UPDATE cases
        SET transcript = CASE
                WHEN %s::text IS NULL THEN transcript
                WHEN decided_at IS NOT NULL AND decided_at <= %s THEN NULL
                ELSE %s::text END,
            claims = CASE
                WHEN %s::jsonb IS NULL THEN claims
                WHEN decided_at IS NOT NULL AND decided_at <= %s THEN NULL
                ELSE %s::jsonb END,
            pattern_id = COALESCE(%s, pattern_id),
            audio_deleted_at = CASE
                WHEN %s THEN COALESCE(audio_deleted_at, %s)
                ELSE audio_deleted_at END
        WHERE id = %s
        """,
        (
            transcript,
            now - TEXT_RETENTION,
            transcript,
            None if claims is None else Jsonb(claims),
            now - TEXT_RETENTION,
            None if claims is None else Jsonb(claims),
            pattern_id,
            audio_deleted,
            now,
            case_id,
        ),
    )


def purge_case_text(conn, *, now: datetime, retention: timedelta = TEXT_RETENTION) -> int:
    """Delete the transcript, the parent's text, and the claims of cases decided
    at least `retention` ago. The result, the pattern id, the timeline, and the
    member stay. Returns how many cases changed. The caller commits.
    """
    _require_aware(now, "now")
    rows = _all(
        conn,
        """
        UPDATE cases
        SET transcript = NULL, parent_text = '', claims = NULL
        WHERE decided_at IS NOT NULL
          AND decided_at <= %s
          AND (transcript IS NOT NULL OR parent_text <> '' OR claims IS NOT NULL)
        RETURNING id
        """,
        (now - retention,),
    )
    return len(rows)


def call_code(conn, case_id: UUID, *, now: datetime) -> str | None:
    """Digits derived from the stored nonce, or None when none can be shown.

    None means the case has no nonce, the code was used, or `now` is at or
    after `one_time_code_expires_at`. The nonce stays in the row.
    """
    _require_aware(now, "now")
    row = _load(conn, case_id, lock=False)
    if row is None:
        raise CaseNotFound(str(case_id))
    nonce = row["one_time_nonce"]
    if nonce is None or row["one_time_code_used_at"] is not None:
        return None
    expires_at = row["one_time_code_expires_at"]
    _require_aware(expires_at, "expires_at")
    if now >= expires_at:
        return None
    if not isinstance(nonce, bytes):
        nonce = bytes(nonce)
    return derive_one_time(case_id, nonce)


def _write_transition(
    conn,
    row: dict,
    updated: dict,
    *,
    now: datetime,
    step: str,
    rng,
    used_at,
) -> None:
    nonce = row["one_time_nonce"]
    code_hash = row["one_time_code_hash"]
    expires_at = row["one_time_code_expires_at"]
    if (
        updated["state"] == "calling"
        and row["state"] != "calling"
        and updated.get("code_channel") == "one_time"
        and nonce is None
    ):
        issued = issue_one_time({**updated, "id": row["id"]}, now=now, rng=rng)
        if issued is not None:
            nonce = issued.nonce
            code_hash = issued.code_hash
            expires_at = issued.expires_at
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
            one_time_nonce = %s,
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
            nonce,
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
        "one_time_nonce": row["one_time_nonce"],
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


def _bind_child_user(conn, member_id: UUID, user_id: UUID) -> None:
    user = _one(conn, "SELECT id FROM users WHERE id = %s", (user_id,))
    if user is None:
        raise ValueError("user_not_found")
    rows = _all(
        conn,
        """
        SELECT id, status
        FROM family_members
        WHERE user_id = %s
        FOR UPDATE
        """,
        (user_id,),
    )
    for row in rows:
        if row["id"] == member_id:
            continue
        if row["status"] != "removed":
            raise ValueError("user_already_in_a_family")


def _user_id(conn, auth_provider: str, auth_subject: str) -> UUID | None:
    row = _one(
        conn,
        """
        SELECT id
        FROM users
        WHERE auth_provider = %s AND auth_subject = %s
        """,
        (auth_provider, auth_subject),
    )
    if row is None:
        return None
    return row["id"]


def _lock_pending_child(conn, member_id: UUID) -> dict:
    row = _one(
        conn,
        """
        SELECT id, family_id, role, status, user_id, phone_opted_in_at
        FROM family_members
        WHERE id = %s
        FOR UPDATE
        """,
        (member_id,),
    )
    if row is None or row["role"] != "child":
        raise CaseNotFound(str(member_id))
    if row["status"] != "invited":
        raise ValueError("member_not_pending")
    return row


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
        ORDER BY seq ASC
        """,
        (case_id,),
    )
    return [row["step"] for row in rows]


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
