-- Family Shield product schema (milestones 3 and 5).
-- Postgres 13 or newer (gen_random_uuid, timestamptz). There is no SQLite schema.
--
-- Local test database, from docker-compose.yml:
--   docker compose up -d
-- Apply this file to that empty database:
--   psql "$DATABASE_URL" -f backend/schema.sql
-- The tests apply it themselves, into their own schema. If Postgres is not
-- running, pytest skips, and the skip message includes: docker compose up -d
--
-- No miss-counter column and no plaintext code column. The one-time digits
-- are not stored: one_time_nonce is 16 random bytes, and the digits are
-- derived from that nonce and OTP_DERIVATION_KEY. The slow-check count is
-- not a column either: it is the count of case_events rows whose step is
-- code_check_slow. The 24-hour static lock counts step static_code_mismatch.
-- Those rows store the outcome, not the digits.

CREATE TABLE users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_provider text NOT NULL,
    auth_subject text NOT NULL,
    display_name text NOT NULL,
    locale text NOT NULL,
    created_at timestamptz NOT NULL,
    CONSTRAINT users_auth_provider_known CHECK (auth_provider IN ('apple', 'google')),
    CONSTRAINT users_locale_known CHECK (locale IN ('en', 'ko')),
    CONSTRAINT users_provider_subject_key UNIQUE (auth_provider, auth_subject)
);

CREATE TABLE sessions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users (id),
    token_hash text NOT NULL,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    CONSTRAINT sessions_token_hash_not_plaintext CHECK (length(token_hash) >= 32)
);

CREATE TABLE families (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    created_by uuid NOT NULL REFERENCES users (id),
    created_at timestamptz NOT NULL
);

CREATE TABLE family_members (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id uuid NOT NULL REFERENCES families (id),
    user_id uuid REFERENCES users (id),
    role text NOT NULL,
    display_name text NOT NULL,
    status text NOT NULL,
    phone_e164 text,
    phone_opted_in_at timestamptz,
    phone_current_since timestamptz,
    pending_phone_e164 text,
    pending_phone_set_at timestamptz,
    push_token text,
    push_provider text,
    push_env text,
    code_hash text,
    code_salt bytea,
    code_set_at timestamptz,
    invite_hash text,
    invite_expires_at timestamptz,
    -- Milestone 16: the SMS allow link for a child with no app. Hash only.
    allow_hash text,
    allow_expires_at timestamptz,
    confirmed_by_parent_at timestamptz,
    created_at timestamptz NOT NULL,
    CONSTRAINT family_members_id_family_key UNIQUE (id, family_id),
    CONSTRAINT family_members_role_known CHECK (role IN ('parent', 'child')),
    CONSTRAINT family_members_status_known CHECK (status IN ('invited', 'active', 'removed')),
    CONSTRAINT family_members_phone_e164_format CHECK (
        phone_e164 IS NULL OR phone_e164 ~ '^\+[1-9][0-9]{1,14}$'
    ),
    CONSTRAINT family_members_pending_phone_format CHECK (
        pending_phone_e164 IS NULL OR pending_phone_e164 ~ '^\+[1-9][0-9]{1,14}$'
    ),
    CONSTRAINT family_members_phone_opt_in_requires_phone CHECK (
        phone_opted_in_at IS NULL OR phone_e164 IS NOT NULL
    ),
    CONSTRAINT family_members_phone_current_since_requires_phone CHECK (
        phone_current_since IS NULL OR phone_e164 IS NOT NULL
    ),
    CONSTRAINT family_members_pending_phone_parts CHECK (
        (
            pending_phone_e164 IS NULL
            AND pending_phone_set_at IS NULL
        )
        OR (
            pending_phone_e164 IS NOT NULL
            AND pending_phone_set_at IS NOT NULL
        )
    ),
    CONSTRAINT family_members_push_shape CHECK (
        (
            push_provider IS NULL
            AND push_token IS NULL
            AND push_env IS NULL
        )
        OR (
            push_provider = 'fcm'
            AND push_token IS NOT NULL
            AND push_env IS NULL
        )
        OR (
            push_provider = 'apns'
            AND push_token IS NOT NULL
            AND push_env IN ('sandbox', 'production')
        )
    ),
    CONSTRAINT family_members_push_token_not_blank CHECK (
        push_token IS NULL OR length(btrim(push_token)) > 0
    ),
    CONSTRAINT family_members_static_code_parts CHECK (
        (
            code_hash IS NULL
            AND code_salt IS NULL
            AND code_set_at IS NULL
        )
        OR (
            code_hash IS NOT NULL
            AND code_salt IS NOT NULL
            AND code_set_at IS NOT NULL
        )
    ),
    CONSTRAINT family_members_static_code_hash_is_phc CHECK (
        code_hash IS NULL OR code_hash LIKE '$argon2id$%'
    ),
    CONSTRAINT family_members_code_salt_len CHECK (
        code_salt IS NULL OR octet_length(code_salt) >= 16
    ),
    CONSTRAINT family_members_code_is_child_only CHECK (
        role = 'child'
        OR (
            code_hash IS NULL
            AND code_salt IS NULL
            AND code_set_at IS NULL
        )
    ),
    CONSTRAINT family_members_invite_parts CHECK (
        (
            invite_hash IS NULL
            AND invite_expires_at IS NULL
        )
        OR (
            invite_hash IS NOT NULL
            AND invite_expires_at IS NOT NULL
        )
    ),
    CONSTRAINT family_members_invite_hash_not_plaintext CHECK (
        invite_hash IS NULL OR length(invite_hash) >= 32
    ),
    CONSTRAINT family_members_allow_parts CHECK (
        (allow_hash IS NULL AND allow_expires_at IS NULL)
        OR (allow_hash IS NOT NULL AND allow_expires_at IS NOT NULL)
    ),
    CONSTRAINT family_members_allow_hash_not_plaintext CHECK (
        allow_hash IS NULL OR length(allow_hash) >= 32
    ),
    CONSTRAINT family_members_allow_is_call_only CHECK (
        allow_hash IS NULL OR (role = 'child' AND user_id IS NULL)
    )
);

-- One non-removed membership per current phone, and per pending phone.
-- A number that is one member's phone_e164 and another's pending_phone_e164
-- is rejected by the store, because one index cannot cover both columns.
CREATE UNIQUE INDEX family_members_phone_e164_active
    ON family_members (phone_e164)
    WHERE status <> 'removed' AND phone_e164 IS NOT NULL;

CREATE UNIQUE INDEX family_members_pending_phone_active
    ON family_members (pending_phone_e164)
    WHERE status <> 'removed' AND pending_phone_e164 IS NOT NULL;

CREATE UNIQUE INDEX family_members_allow_hash_key
    ON family_members (allow_hash)
    WHERE allow_hash IS NOT NULL;

-- An invite is found by its hash (milestone 5), so two live rows cannot share one.
CREATE UNIQUE INDEX family_members_invite_hash_key
    ON family_members (invite_hash)
    WHERE invite_hash IS NOT NULL;

CREATE INDEX family_members_family_id_status_idx
    ON family_members (family_id, status);

CREATE INDEX family_members_user_id_idx
    ON family_members (user_id);

CREATE TABLE cases (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id uuid NOT NULL REFERENCES families (id),
    opened_by uuid NOT NULL REFERENCES users (id),
    child_member_id uuid NOT NULL,
    state text NOT NULL,
    result text,
    answered_via text,
    parent_text text NOT NULL DEFAULT '',
    transcript text,
    claims jsonb,
    pattern_id text,
    code_channel text,
    one_time_nonce bytea,
    one_time_code_hash text,
    one_time_code_expires_at timestamptz,
    one_time_code_used_at timestamptz,
    deadline_at timestamptz,
    audio_deleted_at timestamptz,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    decided_at timestamptz,
    CONSTRAINT cases_child_family_fkey
        FOREIGN KEY (child_member_id, family_id)
        REFERENCES family_members (id, family_id),
    CONSTRAINT cases_state_known CHECK (
        state IN (
            'opened',
            'waiting_push',
            'calling',
            'awaiting_answer',
            'confirmed',
            'scam',
            'not_confirmed'
        )
    ),
    CONSTRAINT cases_code_channel_known CHECK (
        code_channel IS NULL OR code_channel IN ('one_time', 'static')
    ),
    -- IS TRUE, not a bare boolean: in Postgres a CHECK of NULL succeeds,
    -- and `answered_via IN (...)` is NULL when the column is NULL.
    CONSTRAINT cases_result_matches_state CHECK ((
        (
            state IN ('opened', 'waiting_push', 'calling', 'awaiting_answer')
            AND result IS NULL
            AND answered_via IS NULL
            AND decided_at IS NULL
        )
        OR (
            state = 'confirmed'
            AND result = 'sent'
            AND answered_via IN ('push', 'call')
            AND decided_at IS NOT NULL
        )
        OR (
            state = 'scam'
            AND result = 'not_sent'
            AND answered_via IN ('push', 'call')
            AND decided_at IS NOT NULL
        )
        OR (
            state = 'not_confirmed'
            AND result IN (
                'wrong',
                'no_answer',
                'no_number',
                'call_failed',
                'timeout',
                'unreachable',
                'code_locked',
                'number_recent'
            )
            AND answered_via IS NULL
            AND decided_at IS NOT NULL
        )
    ) IS TRUE),
    CONSTRAINT cases_one_time_hash_is_hmac CHECK (
        one_time_code_hash IS NULL OR one_time_code_hash ~ '^[0-9a-f]{64}$'
    ),
    CONSTRAINT cases_one_time_nonce_len CHECK (
        one_time_nonce IS NULL OR octet_length(one_time_nonce) = 16
    ),
    CONSTRAINT cases_one_time_parts CHECK (
        (
            one_time_nonce IS NULL
            AND one_time_code_hash IS NULL
            AND one_time_code_expires_at IS NULL
            AND one_time_code_used_at IS NULL
        )
        OR (
            one_time_nonce IS NOT NULL
            AND one_time_code_hash IS NOT NULL
            AND one_time_code_expires_at IS NOT NULL
        )
    ),
    CONSTRAINT cases_pattern_id_known CHECK (
        pattern_id IS NULL OR pattern_id IN (
            'fake_arrest_bail',
            'accident',
            'gift_card',
            'crypto_or_wire',
            'secrecy',
            'tuition_or_school',
            'new_number',
            'none'
        )
    )
);

CREATE INDEX cases_child_member_id_created_at_idx
    ON cases (child_member_id, created_at);

CREATE INDEX cases_deadline_at_idx
    ON cases (deadline_at);

CREATE INDEX cases_family_id_idx
    ON cases (family_id);

CREATE TABLE verification_attempts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id uuid NOT NULL REFERENCES cases (id),
    channel text NOT NULL,
    status text NOT NULL,
    provider text NOT NULL,
    provider_ref text,
    started_at timestamptz NOT NULL,
    ended_at timestamptz,
    CONSTRAINT verification_attempts_channel_known CHECK (channel IN ('push', 'call')),
    CONSTRAINT verification_attempts_status_known CHECK (
        status IN ('sending', 'sent', 'failed', 'superseded')
    ),
    CONSTRAINT verification_attempts_provider_known CHECK (
        provider IN ('apns', 'fcm', 'twilio')
    )
);

CREATE INDEX verification_attempts_case_id_idx
    ON verification_attempts (case_id);

-- seq is the insertion order. Events for one case are written under that
-- case's row lock, so seq is the order they happened in. Several events in
-- one transaction share `at`, and a random id cannot break that tie.
CREATE TABLE case_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    seq bigint GENERATED ALWAYS AS IDENTITY,
    case_id uuid NOT NULL REFERENCES cases (id),
    at timestamptz NOT NULL,
    step text NOT NULL
);

COMMENT ON COLUMN case_events.step IS
    'Timeline id. static_code_mismatch counts toward the static-code lock. No keypad digits and no transcript.';

CREATE INDEX case_events_case_id_at_idx
    ON case_events (case_id, at);

CREATE INDEX case_events_case_id_seq_idx
    ON case_events (case_id, seq);

CREATE INDEX case_events_case_id_step_idx
    ON case_events (case_id, step);

CREATE TABLE family_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    seq bigint GENERATED ALWAYS AS IDENTITY,
    family_id uuid NOT NULL REFERENCES families (id),
    at timestamptz NOT NULL,
    actor_user_id uuid REFERENCES users (id),
    step text NOT NULL
);

CREATE INDEX family_events_family_id_at_idx
    ON family_events (family_id, at);

-- One SMS OTP challenge (milestone 5). It belongs to the membership that
-- asked for it, so another account cannot finish it. A new challenge for
-- the same member consumes the older ones, and created_at is what the
-- daily send cap counts. code_hash is HMAC(CODE_PEPPER, phone:code).
CREATE TABLE phone_otp (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id uuid NOT NULL REFERENCES family_members (id),
    phone_e164 text NOT NULL,
    code_hash text NOT NULL,
    expires_at timestamptz NOT NULL,
    attempts integer NOT NULL DEFAULT 0,
    consumed_at timestamptz,
    created_at timestamptz NOT NULL,
    CONSTRAINT phone_otp_phone_format CHECK (phone_e164 ~ '^\+[1-9][0-9]{1,14}$'),
    CONSTRAINT phone_otp_code_hash_not_plaintext CHECK (
        length(code_hash) >= 32 AND code_hash !~ '^[0-9]{6}$'
    ),
    CONSTRAINT phone_otp_attempts_non_negative CHECK (attempts >= 0)
);

CREATE INDEX phone_otp_phone_e164_idx
    ON phone_otp (phone_e164);

CREATE INDEX phone_otp_member_id_created_at_idx
    ON phone_otp (member_id, created_at);

CREATE INDEX sessions_user_id_idx
    ON sessions (user_id);

CREATE INDEX families_created_by_idx
    ON families (created_by);

-- A sign-in nonce (milestone 12). POST /v1/auth/nonce issues a raw value;
-- only keyed_hash("signin_nonce", raw) is stored. Apple and Google sign-in
-- consume it once, before expires_at, in the transaction that creates the
-- session, so a captured ID token cannot be replayed with its nonce.
CREATE TABLE signin_nonces (
    nonce_hash text PRIMARY KEY,
    expires_at timestamptz NOT NULL,
    consumed_at timestamptz,
    CONSTRAINT signin_nonces_nonce_hash_not_plaintext CHECK (nonce_hash ~ '^[0-9a-f]{64}$')
);

CREATE INDEX signin_nonces_expires_at_idx
    ON signin_nonces (expires_at);

CREATE INDEX cases_family_id_created_at_idx
    ON cases (family_id, created_at);
