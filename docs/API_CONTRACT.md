# Family Shield API contract (mobile clients)

The contract the iOS and Android apps build against. It is derived only from
`backend/api.py`, `backend/store.py`, `backend/verify.py`, `backend/codes.py`,
`backend/enroll.py`, `backend/signin.py`, `backend/push.py`,
`backend/allow_page.py`, `backend/schema.sql`, and `tests/`. Where the code
is silent or surprising, the text says so ("Note"). If this file and the code
disagree, the code wins and this file is the bug.

## 1. Conventions

| Topic | Rule |
| --- | --- |
| Encoding | JSON request and response bodies (`application/json`), UTF-8. `POST /v1/cases` also accepts `multipart/form-data`. |
| Ids | UUID strings. A path id that is not a UUID is `404 not_found`. |
| Times | ISO-8601 with offset and microseconds, from Python `isoformat()`, e.g. `2026-11-05T07:00:51.061166+00:00`. `null` when unset. |
| Phone input | E.164, regex `^\+[1-9][0-9]{1,14}$`, at most 16 characters (a longer string fails body validation: `400 invalid_body`). Only `+1` (whole NANP) and `+82` are accepted; any other valid E.164 is `400 unsupported_country`, malformed is `400 invalid_phone`. |
| Phone output | Never a full number. Only `phone_last4` / `pending_phone_last4` (last 4 characters of the E.164). |
| Locale | `"en"` or `"ko"` wherever a `locale` field exists. Anything else is `400 invalid_body`. |
| Error body | `{"error": "<code>"}` and nothing else, for every error the `/v1/*` handlers produce. The `/allow/*` pages answer errors as HTML, and `/voice/*` answers `403`/`404` with an empty body. |
| Unknown body fields | Every JSON body model is `extra="forbid"`: an extra field is `400 invalid_body`. Send only the documented fields. |
| Validation order | FastAPI validates the JSON body (and `?limit`) **before** the handler runs, so a malformed body is `400 invalid_body` even with no `Authorization` header. Exception: `POST /v1/cases` checks the bearer shape first. |
| Framework errors | An unregistered path (including every `/v1/dev/*` route when `DEV_AUTH` is off, and every `/voice/*` route when Twilio is not configured) is `404 {"detail":"Not Found"}`; a wrong method is `405 {"detail":"Method Not Allowed"}`. These bodies use `detail`, not `error`. `GET /docs`, `/docs/oauth2-redirect`, `/redoc`, and `/openapi.json` are registered only when `DEV_AUTH=1` and then answer `200`. With `DEV_AUTH` off they are not registered and answer `404 {"detail":"Not Found"}`. |
| Server errors | `500 unavailable` (unexpected exception, transaction rolled back), `500 config` (server misconfiguration, e.g. missing pepper or a naive clock). |

### Errors any authenticated route can return

| Status | `error` | When |
| --- | --- | --- |
| 400 | `invalid_body` | Body/query failed validation (missing field, wrong type, over `max_length`, extra field), or a handler-level value check failed. |
| 401 | `unauthorized` | Missing, malformed, unknown, expired, or revoked session token. |
| 500 | `unavailable` / `config` | See above. |

These are not repeated in the per-route tables below.

## 2. Auth header and sessions

`Authorization: Bearer <token>`

- The scheme must be exactly `Bearer` (case-sensitive), one space, then the token. The token may not contain a space and is at most 512 characters. Anything else is `401 unauthorized`.
- Tokens come from `POST /v1/auth/apple`, `POST /v1/auth/google`, or (DEV_AUTH only) `POST /v1/dev/login`. A token is 43 URL-safe base64 characters (`secrets.token_urlsafe(32)`); the server stores only its SHA-256 hex.
- Sessions last 30 days from issue. There is no refresh, logout, or revoke route; on `401` the app signs in again.
- Store the token in the Keystore-backed store (Android) or Keychain (iOS).

### Roles used in this document

| Role | Meaning in code |
| --- | --- |
| any session | Any valid token. |
| parent of F | The caller has a `family_members` row in family F with `role=parent`, `status=active` (`active_parent`). Failing this is `404 not_found` on family routes (the family's existence is not revealed). |
| child (enrolling) | The caller has exactly one non-removed `role=child` membership (`child_membership`). Failing this is `403 not_a_child` on the OTP routes. |
| child of case C | The case's `child_member_id` row has `user_id` = caller. |

A user can be in at most one family: creating a family needs no membership; accepting an invite needs no other non-removed membership.

## 3. Sign-in sequence (Apple / Google)

1. `POST /v1/auth/nonce` (no auth) returns `{nonce, expires_at}`. `nonce` is the **raw** value, 43 URL-safe base64 characters, single use, valid 10 minutes.
2. The app computes `sha256(raw)` as **lowercase hex** (64 chars) and passes that hex string to Google (`GetGoogleIdTokenOption.setNonce` / Credential Manager) or Apple (`ASAuthorizationAppleIDRequest.nonce`) as the request nonce.
3. The provider returns an ID token whose `nonce` claim is that hex string.
4. `POST /v1/auth/google` (or `/apple`) with `{id_token, nonce: <raw>, locale, display_name?}`. Send the **raw** nonce, not the hex.
5. The server checks: raw nonce shape `[A-Za-z0-9_-]{32,128}`; RS256 signature against the provider JWKS; `aud` = pinned audience (Google: `GOOGLE_SERVER_CLIENT_ID`, i.e. the server/web client id the Android app requests the token for; Apple: the bundle id); `iss`; `exp`/`iat`/`nbf` with 60 s leeway; `sub`; `nonce` claim == sha256 hex of raw. Then it spends the stored nonce (unknown, already used, or expired fails) and creates the session, all in one transaction.
6. Any failure in 5 is `401 invalid_token`. A failure before the spend leaves the nonce unspent, but the app should fetch a fresh nonce for every attempt.

Only `sub` is trusted. Email and the token's name claim are ignored. `display_name` and `locale` are written only when the user row is first created; later sign-ins do not change them (the locale is updated later by `POST /v1/me/push-token`).

## 4. Route index

`DEV` = registered only when the server runs with `DEV_AUTH=1` (never in production; otherwise `404 {"detail":"Not Found"}`).

| Method | Path | Caller | Success |
| --- | --- | --- | --- |
| POST | `/v1/auth/nonce` | public | 201 |
| POST | `/v1/auth/apple` | public | 200 |
| POST | `/v1/auth/google` | public | 200 |
| POST | `/v1/dev/login` | public, **DEV** | 201 |
| GET | `/v1/me` | any session | 200 |
| POST | `/v1/families` | any session with no membership | 201 |
| POST | `/v1/families/{family_id}/children` | parent of family | 201 |
| GET | `/v1/families/{family_id}/members` | parent of family | 200 |
| GET | `/v1/families/{family_id}/cases?limit=N` | parent of family | 200 |
| POST | `/v1/families/{family_id}/members/{member_id}/invite` | parent of family | 201 |
| POST | `/v1/families/{family_id}/members/{member_id}/confirm` | parent of family | 200 |
| POST | `/v1/families/{family_id}/members/{member_id}/phone-change` | parent of family | 200 |
| POST | `/v1/families/{family_id}/members/{member_id}/call-only` | parent of family | 202 |
| POST | `/v1/families/{family_id}/members/{member_id}/allow-link` | parent of family | 202 |
| POST | `/v1/invites/accept` | any session | 200 |
| POST | `/v1/phones/otp` | child (enrolling) | 202 |
| POST | `/v1/phones/otp/check` | child (enrolling) | 200 |
| POST | `/v1/me/check-code` | child | 200 |
| POST | `/v1/me/push-token` | child, or single active parent | 200 |
| POST | `/v1/cases` | parent of the child's family | 201 |
| GET | `/v1/cases/{case_id}` | parent of family, or child of case | 200 |
| POST | `/v1/cases/{case_id}/answer` | child of case | 200 |
| GET | `/v1/cases/{case_id}/call-code` | child of case | 200 |
| POST | `/v1/dev/members/{member_id}/activate` | parent, **DEV** | 201 |
| POST | `/v1/dev/members/{member_id}/check-code` | parent, **DEV** | 200 |
| POST | `/v1/dev/cases/{case_id}/digits` | parent of family or child of case, **DEV** | 200 |
| GET/POST | `/allow/{secret}`, `/allow/{secret}/otp`, `/allow/{secret}/confirm` | browser (SMS link), HTML | 200 |
| GET | `/voice/prompts/{language}/{name}.mp3` | Twilio only (unsigned) | 200 `audio/mpeg` |
| POST | `/voice/twilio/{outbound,code,answer,status}` | Twilio only (signed) | 200 TwiML |
| GET | `/docs`, `/docs/oauth2-redirect`, `/redoc`, `/openapi.json` | public, **DEV** | 200 |

## 5. Routes

### Auth

**POST /v1/auth/nonce** — no body, no auth.

| Response 201 | Type | Meaning |
| --- | --- | --- |
| `nonce` | string | Raw nonce (43 chars). Hash it for the provider; post it raw to sign-in. |
| `expires_at` | time | Issue time + 10 min. |

Errors: `500 config` / `500 unavailable` only. Expired rows are deleted on each issue. No rate limit.

**POST /v1/auth/google**, **POST /v1/auth/apple** — no auth.

| Body | Type | Limits |
| --- | --- | --- |
| `id_token` | string | required, ≤ 8192 chars |
| `nonce` | string | required, raw nonce, ≤ 128 chars |
| `locale` | string | required, `en`/`ko` |
| `display_name` | string \| null | optional, ≤ 200 chars, trimmed; `""` when omitted |

| Response 200 | Type | Meaning |
| --- | --- | --- |
| `token` | string | Session token (30 days). |
| `user_id` | uuid | The user, created on first sign-in for this `(provider, sub)`. |

| Error | When |
| --- | --- |
| 400 `invalid_body` | Validation, or `locale` not `en`/`ko`. |
| 401 `invalid_token` | Nonce shape, token signature/audience/issuer/times/subject, nonce claim mismatch, or nonce unknown/spent/expired. |
| 503 `sign_in_unavailable` | That provider's audience is not configured (only possible with `DEV_AUTH=1`; production refuses to boot without both). Checked after body validation. |

Note: a Google user who omits `display_name` on first sign-in gets `display_name = ""`, and a family they create gets a parent membership named `""`. The Android app should send the Google account's display name.

**POST /v1/dev/login** — **DEV only**, no auth.

| Body | Type | Limits |
| --- | --- | --- |
| `display_name` | string | required, non-blank after trim, ≤ 200 |
| `locale` | string | required, `en`/`ko` |
| `auth_subject` | string \| null | optional, `[A-Za-z0-9._:-]{1,200}`; omitted or `null` = `dev-<uuid4>` (a new user every time) |

Response 201: `{token, user_id, auth_subject}`. Same `auth_subject` = same user (provider recorded as `apple`). Errors: `400 invalid_body`.

### Me

**GET /v1/me** — any session.

| Response 200 | Type | Meaning |
| --- | --- | --- |
| `user_id` | uuid | |
| `display_name` | string | From first sign-in. |
| `locale` | `en`/`ko` | Last value from sign-up or push-token registration. |
| `memberships[]` | array | Non-removed memberships, oldest first (ties by id). Empty = not in a family yet. |
| `memberships[].member_id` | uuid | Use as `child_member_id` / `member_id`. |
| `memberships[].family_id` | uuid | |
| `memberships[].family_name` | string | |
| `memberships[].role` | `parent`/`child` | |
| `memberships[].status` | `invited`/`active` | |
| `memberships[].display_name` | string | The membership's name (for a child: the name the parent typed). |

The app finds its family here after sign-in: a parent with one `role=parent, status=active` row uses that `family_id`.

### Family and members (parent)

**POST /v1/families** — any session that holds no non-removed membership.

Body: `name` string, required, non-blank after trim, ≤ 200. Response 201: `{id, name}` (trimmed name). The caller becomes an `active` parent member whose `display_name` is the user's display name.

| Error | When |
| --- | --- |
| 400 `invalid_body` | Blank or too long name. |
| 403 `not_a_parent` | Caller already has a child membership. |
| 409 `already_in_a_family` | Caller already has a parent membership. |

**POST /v1/families/{family_id}/children** — parent of family.

Body: `display_name` string, required, non-blank, ≤ 200.

| Response 201 | Type | Meaning |
| --- | --- | --- |
| `id` | uuid | The child's `member_id`. |
| `display_name` | string | Trimmed. |
| `status` | `"invited"` | |
| `invite_secret` | string | `XXXX-XXXX-XXXX`, 12 chars from `23456789ABCDEFGHJKMNPQRSTUVWXYZ`. **Shown once**; only a keyed hash is stored. |
| `invite_expires_at` | time | Now + 24 h. |

Errors: `400 invalid_body`, `404 not_found` (not a parent of that family).

**POST /v1/families/{family_id}/members/{member_id}/invite** — parent of family. No body. Re-issues the secret; the previous secret stops working.

Response 201: `{id, invite_secret, invite_expires_at}`.

| Error | When |
| --- | --- |
| 404 `not_found` | Not a parent of that family; member missing, not in that family, not a child, or removed. |
| 409 `invite_not_open` | The child is not `invited`, or a child account already accepted. |

Note: a call-only child (number added, allow link not yet completed) is still `invited` with no account, so the code allows a re-issue for it. Nothing in the API guards that combination; clients should not offer "re-send invite" when `call_only` is true.

**GET /v1/families/{family_id}/members** — parent of family.

Response 200: `{family_id, members: [...]}`, non-removed members oldest first, **parents included**.

| Member field | Type | Meaning |
| --- | --- | --- |
| `id` | uuid | member id |
| `role` | `parent`/`child` | |
| `display_name` | string | |
| `status` | `invited`/`active` | |
| `linked` | bool | A user account is attached (invite accepted, or a parent). |
| `phone_last4` | string \| null | Current (dialed) number. |
| `pending_phone_last4` | string \| null | A number change waiting for a parent. |
| `phone_verified` | bool | `phone_opted_in_at` set (OTP passed, or allow page completed). |
| `has_check_code` | bool | A 4-digit check code is stored. |
| `awaiting_confirm` | bool | Child, `invited`, linked, and phone verified: show Confirm / Reject. |
| `invite_expires_at` | time \| null | Set while an invite secret is outstanding. **Not cleared on expiry**; compare with now. Cleared on accept and on call-only. |
| `call_only` | bool | No account and a number set (milestone 16 child). |
| `allow_link_open` | bool | An allow link has been issued and not completed. **Not cleared on expiry** (72 h). |
| `confirmed_at` | time \| null | `confirmed_by_parent_at`. Null for parents. |

Errors: `404 not_found`.

**POST /v1/families/{family_id}/members/{member_id}/confirm** — parent of family.

Body: `decision` = `"confirm"` or `"reject"` (≤ 16 chars; anything else `400 invalid_body`).

| Decision | Response 200 | Effect |
| --- | --- | --- |
| `confirm` | `{id, status:"active", phone_last4}` | Child becomes callable; `phone_current_since = now` starts the 24-hour `number_recent` rule. |
| `reject` | `{id, status:"removed"}` | Row removed; invite and number freed. |

| Error | When |
| --- | --- |
| 404 `not_found` | As for `/invite`. |
| 409 `member_not_pending` | Child is not `invited` (e.g. already active). There is no route to remove an active child. |
| 409 `member_not_ready` | `confirm` before the child accepted the invite **and** verified a number (includes every call-only child). `reject` has no such requirement. |

**POST /v1/families/{family_id}/members/{member_id}/phone-change** — parent of family.

Body: `decision` = `"confirm"` / `"reject"`.

| Decision | Response 200 | Effect |
| --- | --- | --- |
| `confirm` | `{id, status:"changed", phone_last4, cancelled_cases}` | Pending number becomes the dial target; every open case of this child ends `not_confirmed`/`timeout` (timeline `phone_number_changed`); `cancelled_cases` is how many; `phone_current_since = now`. Pushes `number_change_confirmed` and texts the old number. |
| `reject` | `{id, status:"kept"}` | Pending number dropped. No notice is sent. |

Errors: `400 invalid_body`, `404 not_found`, `409 no_pending_number` (no pending number, or for confirm the child is not `active`). `409 phone_in_use` is possible if a unique index races.

**POST /v1/families/{family_id}/members/{member_id}/call-only** — parent of family. Milestone 16, a child with no app.

Body: `phone_e164` (≤ 16). Sets the number and `confirmed_by_parent_at`, **not** the opt-in; drops the app invite; texts the number an allow link (`{PUBLIC_BASE_URL}/allow/{secret}`, valid 72 h).

Response 202: `{status:"link_sent", phone_last4}`.

| Error | When |
| --- | --- |
| 503 `otp_unavailable` | No SMS sender (checked first, before auth). |
| 503 `allow_link_unavailable` | `PUBLIC_BASE_URL` blank (also checked before auth). **The local DEV_AUTH e2e backend has it blank, so this route always answers 503 there.** |
| 404 `not_found` | Not a parent / not a child of that family. |
| 400 `invalid_phone` / `unsupported_country` | |
| 409 `not_call_only` | Child is not `invited`, already has an account, or already has a number. |
| 409 `phone_in_use` | Another non-removed member has this number (current or pending). |
| 502 `sms_failed` | Sending failed **after** commit: the number and link are saved; retry with `/allow-link`. |

The child is not callable until they open the link, tap Allow, pass the SMS code, and set a check code (`phone_verified` and `status` become true/`active`).

**POST /v1/families/{family_id}/members/{member_id}/allow-link** — parent of family. No body. A new link for a call-only child (first opt-in again, or a forgotten check code); it replaces the old link and does not move `phone_current_since`.

Response 202: `{status:"link_sent", phone_last4}`. Errors: the two `503`s, `404 not_found`, `409 not_call_only` (child has an account, no number, or no parent confirmation), `502 sms_failed`.

### Child enrollment

**POST /v1/invites/accept** — any session.

Body: `secret` string ≤ 64. Spaces and dashes are removed and it is uppercased, so `gp9b 8gku dcvn` works.

Response 200: `{member_id, family_id, display_name, status:"invited"}`. The secret is burned.

| Error | When |
| --- | --- |
| 400 `invite_invalid` | Wrong shape, unknown, used, or replaced secret. |
| 400 `invite_expired` | Past 24 h (stays this answer until the parent re-issues). |
| 409 `already_in_a_family` | Caller already has another non-removed membership (parent or child). |

**POST /v1/phones/otp** — child (enrolling). Starts SMS (or voice) OTP, 6 digits, valid 10 minutes. Two modes:

- *Enrollment*: child is `invited` with no number.
- *Number change*: child is `active` with a number. Requires `biometric_ok: true` (the app's BiometricPrompt passed).

| Body | Type | Limits |
| --- | --- | --- |
| `phone_e164` | string | ≤ 16, `+1`/`+82` |
| `channel` | string | `sms` (default) or `voice` (code read aloud by a call; for Korean carriers that block SMS) |
| `biometric_ok` | bool | default `false` |

Response 202: `{status:"sent", channel, phone_last4, expires_at}`.

| Error | When (in this order) |
| --- | --- |
| 503 `otp_unavailable` | No SMS sender (not reachable with the normal boot). |
| 403 `not_a_child` | Caller is not exactly one non-removed child. |
| 400 `invalid_body` | `channel` not `sms`/`voice`. |
| 403 `biometric_required` | Change mode without `biometric_ok: true`. |
| 409 `same_number` | Change mode, number equals the current one. |
| 409 `phone_already_set` | Enrollment mode but the child already has a number, or not `invited`. |
| 400 `invalid_phone` / `unsupported_country` | |
| 429 `rate_limited` | 5 challenges for this member in the rolling 24 h (every start counts, used or not). |
| 502 `sms_failed` | Provider refused **after** commit (the challenge exists and counts toward the cap). |

A new start consumes the member's older live challenges. The number is not checked for uniqueness until `/check`.

**POST /v1/phones/otp/check** — child (enrolling).

Body: `phone_e164` (≤ 16), `code` string (≤ 16; anything but 6 ASCII digits counts as a miss).

| Mode | Response 200 | Effect |
| --- | --- | --- |
| Enrollment | `{status:"verified", phone_last4}` | Number attached and opted in. Parent's roster now shows `awaiting_confirm: true`. |
| Change | `{status:"pending_parent", phone_last4}` | Stored as pending; the old number is still dialed. Pushes `number_change_requested` to parents and the child's device, and texts the old number. |

| Error | When |
| --- | --- |
| 503 `otp_unavailable`, 403 `not_a_child`, 400 `invalid_phone`/`unsupported_country` | As above. |
| 409 `phone_already_set` | Child already has a number and is not in change mode. |
| 409 `same_number` | Change mode with the current number. |
| 400 `otp_wrong` | Miss; the attempt is committed. The 5th miss kills the challenge. |
| 400 `otp_expired` | No live challenge for this member and number: expired, consumed, 5 misses reached, or never started. Start a new one. |
| 409 `phone_in_use` | Another non-removed member holds this number (current or pending). |
| 400 `member_not_callable` | The membership was removed meanwhile. |
| 409 `no_current_phone` | Change mode raced with a member that has no number. |

**POST /v1/me/check-code** — caller with exactly one non-removed child membership (any status).

| Body | Type | Limits |
| --- | --- | --- |
| `code` | string | ≤ 16; must be exactly 4 ASCII digits |
| `biometric_ok` | bool | required. Not needed for the first set; required `true` to replace an existing code. |

Response 200: `{status:"set"}`. Replacing a code clears the 5-miss static lock. The code is never returned.

Errors: `403 not_a_child`, `400 invalid_code` (not 4 digits), `403 biometric_required` (replacement without `biometric_ok: true`). On a replacement the biometric is checked before the code's shape, so a malformed replacement with `biometric_ok: false` is `403 biometric_required`.

**POST /v1/me/push-token** — a child (one non-removed child membership), else a user with exactly one `active` parent membership.

| Body | Type | Limits |
| --- | --- | --- |
| `provider` | string | `fcm` or `apns` (≤ 8) |
| `token` | string | ≤ 4096; trimmed; non-empty; no whitespace inside |
| `env` | string \| null | ≤ 16. `apns`: `sandbox` or `production` (required). `fcm`: must be absent or `null`. |
| `locale` | string | `en`/`ko` (≤ 8); also written to the user's `locale` |

Response 200: `{status:"registered", provider}`. One token = one device: if another membership held this token, it loses it. A child's token makes cases ask by push first; a parent's token receives number-change notices only.

Errors: `400 invalid_body` (any rule above), `403 not_a_member`. The membership is resolved first, so a caller with no qualifying membership gets `403 not_a_member` even when the token, provider, env, or locale is also wrong (only `max_length` and type failures are `400` earlier).

### Cases

**POST /v1/cases** — parent of the child's family. JSON, or multipart with a voice note.

JSON body:

| Field | Type | Limits |
| --- | --- | --- |
| `child_member_id` | uuid | required |
| `text` | string | optional, default `""`, ≤ 8000 chars (the suspicious message, as typed or shared) |

Multipart (`multipart/form-data`): fields `child_member_id`, `text`, and file `audio`, each at most once, nothing else. `Content-Length` is required. `audio` must have a `audio/*` content type, be non-empty, and be ≤ 10 MB (10 485 760 bytes; the whole request may be at most 64 KiB more). Any request whose `Content-Type` does not start with `multipart/form-data` is parsed as JSON.

Response 201: the **parent case body** (§6) as it stands after the push or call was handed to the provider. It can already be terminal (e.g. `not_confirmed`/`code_locked` or `call_failed`).

| Error | When (in order) |
| --- | --- |
| 401 `unauthorized` | No well-formed `Bearer` header (checked before the body). |
| 400 `invalid_body` | JSON: unparseable, not an object, or bad/extra fields. |
| 411 `length_required` | Multipart without a numeric `Content-Length`. |
| 413 `audio_too_large` | Multipart `Content-Length` over 10 MB + 64 KiB (checked before the form is read). |
| 400 `invalid_body` | Multipart: unparseable form, unknown or repeated part, non-file `audio`, file in a text field, or bad field values. |
| 415 `unsupported_audio` | `audio` part not `audio/*`. |
| 413 `audio_too_large` | `audio` over 10 MB while streaming. |
| 400 `empty_audio` | Zero-byte `audio`. |
| 401 `unauthorized` | Token not a live session. |
| 404 `not_found` | Member unknown, or caller is not an active parent of that family. |
| 403 `not_a_parent` | Caller is that child. |
| 400 `member_not_callable` | Target is not a child, not `active`, not parent-confirmed, or has neither an opted-in phone nor a push token; also when the start finds no way to reach the child (nothing is saved). |
| 429 `rate_limited` | This parent opened 5 cases for this child, or 10 cases in all, in the rolling 24 h. |

After the response, if audio was sent it is transcribed (Cartesia, language from the parent's locale), then claims and a pattern are read (Claude). Each part is skipped when its key is not configured. The audio file is deleted in all cases. None of this changes state or result; `transcript`, `claims`, and `pattern_id` simply appear later on `GET /v1/cases/{id}`.

**GET /v1/cases/{case_id}** — parent of the case's family gets the parent body; the child of the case gets the child body (§6). Anyone else, or a bad id: `404 not_found`.

**POST /v1/cases/{case_id}/answer** — child of the case only. The in-app Yes/No (after BiometricPrompt).

Body: `answer` = `"yes"` or `"no"` (≤ 8 chars; validated before the case is looked up).

Response 200: child body. `yes` → `confirmed`/`sent`/`answered_via:"push"` (green, even within 24 h of a number change); `no` → `scam`/`not_sent` (red). Valid while `waiting_push`, `calling`, or `awaiting_answer`. On a terminal case it returns the existing result unchanged (first terminal event wins; safe to retry).

Errors: `400 invalid_body`, `403 not_the_child` (a parent), `404 not_found`.

**GET /v1/cases/{case_id}/call-code** — child of the case only. Response header `Cache-Control: no-store`.

| Response 200 | Meaning |
| --- | --- |
| `{"code": "123456"}` | Case is `calling` on the `one_time` channel and the 6-digit code is live (5 min from when the call state was entered, unused). Show it for the child to type on the keypad. |
| `{"code": null, "fallback": "static"}` | No live one-time code; the call asks for (or will ask for) the 4-digit check code. |

Errors: `403 not_the_child` (a parent), `404 not_found`.

### DEV_AUTH-only helpers

| Route | Caller | Body | Response | Errors |
| --- | --- | --- | --- | --- |
| `POST /v1/dev/members/{member_id}/activate` | parent of that child's family | `phone_e164` (≤ 16), `user_id` uuid \| null | 201 `{status:"active", phone_last4}`. Child becomes active, opted in, parent-confirmed, `phone_current_since = now` (first time only); `user_id` links that account (skips invite and OTP). Note: the number is opted in only when the row had no number; a call-only child activated with its existing number stays `phone_verified:false`. | 404 `not_found`, 403 `not_a_parent` (caller is the child), 400 `invalid_phone`/`unsupported_country`, 409 `phone_already_set` (different number), 409 `phone_in_use`, 400 `member_not_callable` (removed), 409 `already_in_a_family` (user in another family), 404 `not_found` (unknown `user_id`) |
| `POST /v1/dev/members/{member_id}/check-code` | parent of that child's family | `code`, `biometric_ok` | 200 `{status:"set"}`. Same rules as `/v1/me/check-code`. | 404 `not_found`, 403 `not_a_parent` (caller is the child), 403 `not_the_child` (the child row has an account: the caller is a parent, so any linked child is refused; a linked child sets its code with `/v1/me/check-code`), 400 `invalid_code`, 403 `biometric_required` |
| `POST /v1/dev/cases/{case_id}/digits` | parent of the family or child of the case | `digits` string ≤ 32 | 200 case body for the caller's role (a terminal case is returned unchanged) | 404 `not_found` |

`/digits` simulates the keypad exactly as the Twilio webhooks do: while `calling`, `*` (or an empty string on the one-time gather) switches to the static code, a single digit is ignored, anything else is a code attempt; while `awaiting_answer`, `1` = yes, `2` = no, anything else = unclear.

### Not for apps

- `/allow/{secret}` pages are server-rendered HTML for the child's browser (language from the number: `+82` Korean, else English). `GET` never changes anything. `POST /otp` sends the SMS code (same 5/day cap and 10 min TTL as the app OTP); `POST /confirm` takes form fields `otp`, `code`, `again` and on success opts the number in, stores the check code, makes the child `active`, and burns the link. Errors are HTML pages, not JSON: an expired, unknown, used, or malformed link (shape `[A-Za-z0-9_-]{32,64}`) is 404, and so is `POST /otp` when there is no SMS sender; the cap is 429; an SMS failure is 502; on `/confirm` a bad or mismatched check code, a wrong SMS code, or a dead SMS challenge is 400 (the check code is validated before the SMS code, so a typo does not spend an attempt).
- `/voice/*` exists only when all of `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `PUBLIC_BASE_URL` are set. `POST /voice/twilio/{kind}` accepts only Twilio-signed requests (bad signature: empty `403`; unknown `kind`: empty `404`), and a webhook whose `CallSid` does not match the case's recorded attempt just hangs up. `GET /voice/prompts/{en|ko}/{name}.mp3` is unsigned and serves the fixed prompt audio (unknown language or name: empty `404`).

## 6. Case model

### Parent body (`GET /v1/cases/{id}` as parent, `POST /v1/cases`, parent `/dev/.../digits`)

| Field | Type | Meaning |
| --- | --- | --- |
| `id`, `family_id`, `child_member_id` | uuid | |
| `child_display_name` | string | Child's membership name (`""` if the member row is gone). |
| `state` | enum | §6 states. Source of truth. |
| `result` | enum \| null | Null while open. |
| `color` | `open`/`green`/`red`/`yellow` | Derived from `state` only. |
| `answered_via` | `push`/`call`/null | Set only for `sent` / `not_sent`. |
| `code_channel` | `one_time`/`static`/null | Which code the call asks for. Null until a call starts. |
| `gather` | `one_time`/`static`/`answer`/null | What the next keypad prompt would ask for. |
| `parent_text` | string | The text the parent posted (`""` if none, and after the 30-day purge). |
| `transcript` | string \| null | Voice note transcript, ≤ 20 000 chars. Untrusted. |
| `claims` | object \| null | `{claimed_identity, amount, story, red_flags: [≤3 strings]}`; any string may be `"unknown"`. Only produced from a transcript (audio), never from `text` alone. Untrusted: show under the fixed "this does NOT prove who it is" heading. |
| `pattern_id` | string \| null | One of `fake_arrest_bail`, `accident`, `gift_card`, `crypto_or_wire`, `secrecy`, `tuition_or_school`, `new_number`, `none`. From the transcript, else from `text`. `en`/`ko` labels live in `backend/patterns.json` (`none` has empty labels); the API sends only the id. |
| `timeline` | string[] | Step ids (§6 timeline) in order. No per-step times. |
| `phone_last4` | string \| null | Child's current number. |
| `deadline_at` | time \| null | End of the current wait window; null in `opened` and terminal states. |
| `created_at`, `updated_at` | time | |
| `decided_at` | time \| null | Set exactly when the state becomes terminal. |

Never present: codes, nonces, hashes, full phone numbers, audio.

### Child body (`CHILD_CASE_KEYS`)

`id`, `child_member_id`, `kind` (always `"money_request"`), `state`, `result`, `color`, `answered_via`, `code_channel`, `gather`, `deadline_at`, `created_at`, `updated_at`, `decided_at`.

The child never sees the parent's text, transcript, claims, pattern, timeline, phone, or names. The question is always the fixed money-request question ("Did you send your family a message asking for money?"), localized on the device.

### States

| State | Open? | Deadline | Meaning |
| --- | --- | --- | --- |
| `opened` | yes | none | Transient inside `POST /v1/cases`; not normally observed. |
| `waiting_push` | yes | 90 s | Child's device was asked by push. |
| `calling` | yes | 180 s | Fallback call; waiting for the code on the keypad. |
| `awaiting_answer` | yes | 45 s | Right code entered; waiting for 1 / 2. |
| `confirmed` | terminal | — | green |
| `scam` | terminal | — | red |
| `not_confirmed` | terminal | — | yellow |

Deadlines are set when a state is entered (switching `one_time`→`static` does not reset it). A background loop applies passed deadlines every `TIMER_SECONDS` (default 5, 1 on the local e2e backend), so a move may lag `deadline_at` by that much.

### Results and colors

| `state` | `result` | `answered_via` | `color` |
| --- | --- | --- | --- |
| any open | `null` | `null` | `open` |
| `confirmed` | `sent` | `push` or `call` | `green` |
| `scam` | `not_sent` | `push` or `call` | `red` |
| `not_confirmed` | `wrong` — wrong code on the call | `null` | `yellow` |
| | `no_answer` — right code, then no/unclear 1-2 answer or hang-up | | |
| | `no_number` — nobody to reach (API turns this into `400 member_not_callable`; not stored) | | |
| | `call_failed` — provider refused the call, or Twilio `failed`/`canceled` | | |
| | `timeout` — push or code window passed, Twilio busy/no-answer, call completed before a code, number change cancelled the case | | |
| | `unreachable` — push token dead and no number | | |
| | `code_locked` — static check code locked (5 misses / 24 h) when the call would have to ask for it: a no-account child at `start` / push fallback, or `*` on an app child's one-time gather | | |
| | `number_recent` — keypad "yes" within 24 h of the number's `phone_current_since` | | |

### Transitions (from `backend/verify.py`)

| Event | Triggered by | From | To |
| --- | --- | --- | --- |
| `start` | `POST /v1/cases` | `opened` | `waiting_push` if the child has a push token; else `calling` (`one_time` if the child has an account, `static` if not) if an opted-in phone; a no-account child with a locked static code → `not_confirmed/code_locked`; else `no_number` |
| `push_answered_yes` / `_no` | `POST /answer` | `waiting_push`, `calling`, `awaiting_answer` | `confirmed/sent` / `scam/not_sent`, via `push` |
| `push_failed` | Provider says the token is permanently dead (token is cleared) | `waiting_push` | `calling` as in `start`, else `not_confirmed/unreachable` |
| `push_window_elapsed` | 90 s | `waiting_push` | `calling` as in `start`, else `not_confirmed/timeout` |
| `call_accepted` | Provider accepted the call | any | no change, no timeline row |
| `call_failed` | Provider refused the call, or Twilio status `failed`/`canceled` | `calling` | `not_confirmed/call_failed` |
| `code_accepted` | Right code | `calling` | `awaiting_answer` |
| `code_rejected` | Wrong / expired / used code, or any code on the static gather while the static code is locked | `calling` | `not_confirmed/wrong` |
| `use_static_code` | `*` (or an empty submission) on the one-time gather | `calling` (`one_time`) | `calling` (`static`), or `not_confirmed/code_locked` if locked |
| `answer_yes` | Keypad 1 | `awaiting_answer` | `confirmed/sent` via `call`, or `not_confirmed/number_recent` |
| `answer_no` | Keypad 2 | `awaiting_answer` | `scam/not_sent` via `call` |
| `answer_unclear` | Any other keypad input | `awaiting_answer` | `not_confirmed/no_answer` |
| `answer_window_elapsed` | 45 s, or the call ended | `awaiting_answer` | `not_confirmed/no_answer` |
| `code_window_elapsed` | 180 s, or Twilio busy / no-answer / completed | `calling` | `not_confirmed/timeout` |
| `cancel` | Parent confirmed a number change | any open | `not_confirmed/timeout` |
| `code_check_slow` | Defined in the machine; **no code path emits it today** | `calling` | (2nd) `not_confirmed/timeout` |

A terminal state never changes again. A push that only fails transiently is not retried; the 90 s window then falls through to the call.

### Timeline step ids

A row is written only when a transition changes the case. The step is the event name unless a more specific id is given. Every id that can appear in `timeline`:

| Step id | Written when |
| --- | --- |
| `start` | Case opened (always first). |
| `push_answered_yes`, `push_answered_no` | In-app answer. |
| `push_failed` | Push token permanently rejected. |
| `push_window_elapsed` | 90 s without an answer. |
| `call_failed` | Call could not be placed, or Twilio reported `failed`/`canceled`. |
| `call_busy`, `call_no_answer` | Twilio reported `busy` / `no-answer` while asking for the code. |
| `call_ended_before_code` | Call completed before a code was accepted. |
| `call_ended_before_answer` | Call ended after the right code, before 1/2. |
| `code_window_elapsed` | 180 s without a code. |
| `use_static_code` | Star (or empty input) on the one-time gather: switched to the 4-digit check code, or ended `code_locked`. |
| `code_accepted` | Right code. |
| `static_code_mismatch` | Wrong static code: any non-empty submission of 2+ digits that is not the stored 4-digit code, or any 4 digits when no code is set (counts toward the 24 h lock). |
| `code_did_not_match` | Wrong, malformed, or already-used 6-digit code. |
| `one_time_code_expired` | Right shape but the one-time code expired. |
| `code_rejected` | Code entered while the static code was already locked. |
| `answer_yes`, `answer_no`, `answer_unclear` | Keypad 1 / 2 / other. |
| `answer_window_elapsed` | 45 s without 1/2. |
| `phone_number_changed` | Cancelled by a confirmed number change. |

(`code_check_slow` is read by the store but never written; `call_accepted` never produces a row.)

Family-level events (`child_invited`, `invite_reissued`, `invite_accepted`, `phone_verified`, `child_confirmed`, `child_rejected`, `number_change_requested`, `number_change_confirmed`, `number_change_rejected`, `call_only_number_added`, `allow_link_sent`, `call_only_allowed`, `call_only_code_reset`) are stored in `family_events`, but **no route returns them**.

### Polling

- After `POST /v1/cases`, poll `GET /v1/cases/{id}` every few seconds (2–3 s is reasonable; there is no websocket or push to the parent for case progress) until `color != "open"` (equivalently `decided_at != null`).
- `deadline_at` tells the UI how long the current step can take; a whole case takes at most about 90 + 180 + 45 s plus timer lag.
- `transcript`, `claims`, `pattern_id` are filled asynchronously and can arrive before or after the case is decided. There is no field that says analysis finished; a parent screen that wants them may poll a little longer after a voice-note case or refresh on open.
- The family list (`GET /v1/families/{id}/cases`) is a summary for the home screen: `{family_id, cases:[{id, child_member_id, child_display_name, state, result, color, created_at, decided_at}]}`, newest first, `limit` 1..50 (default 20; out of range is `400 invalid_body`), no pagination cursor.

## 7. Flows

### Parent enrollment of an app child

| # | Who | Call | Roster after (`GET .../members`, child row) |
| --- | --- | --- | --- |
| 1 | parent | Sign in (§3). `GET /v1/me` → no memberships | |
| 2 | parent | `POST /v1/families {name}` | |
| 3 | parent | `POST /v1/families/{f}/children {display_name}` → show `invite_secret` once; parent shares it over a trusted channel | `invited`, `linked:false`, `invite_expires_at` set |
| 4 | child | Sign in; `POST /v1/invites/accept {secret}` | `linked:true`, `invite_expires_at:null` |
| 5 | child | `POST /v1/phones/otp {phone_e164}` → SMS; `POST /v1/phones/otp/check {phone_e164, code}` | `phone_verified:true`, `phone_last4`, `awaiting_confirm:true` |
| 6 | child | `POST /v1/me/check-code {code, biometric_ok:false}` (first set) | `has_check_code:true` |
| 7 | child | `POST /v1/me/push-token` | (not shown) |
| 8 | parent | Sees "{name} wants to join. Number ending {last4}." → `POST .../confirm {decision:"confirm"}` (or `reject`) | `status:"active"`, `awaiting_confirm:false`, `confirmed_at` set |

Steps 6 and 7 may happen before or after 8. Confirm needs only 4 and 5. The child is a legal case target (`POST /v1/cases` succeeds) once `active` + confirmed + (opted-in phone or push token). An app child's call asks for the one-time code (`call-code`); the check code is the `*` fallback.

UI rule for the parent (from the roster): enable "Verify" for a child only when `role=child`, `status=active`, and `confirmed_at != null`. The server is the final judge (`400 member_not_callable`).

### Call-only child (no app)

1. Parent: `POST /v1/families/{f}/children` (creates the `invited` row), then `POST .../call-only {phone_e164}` → `202 link_sent`. Roster: `call_only:true`, `allow_link_open:true`, `phone_verified:false`, `confirmed_at` set, status still `invited`.
2. Child: opens the SMS link, taps Allow, gets an SMS code, enters it and a 4-digit check code twice.
3. Roster: `status:"active"`, `phone_verified:true`, `has_check_code:true`, `allow_link_open:false`. Cases now go straight to a `static` call. A keypad yes in the first 24 h is `number_recent` (yellow).
4. Forgotten code: `POST .../allow-link` → a new link; completing it replaces the code, keeps `phone_current_since`.

### Number change (app child)

1. Child: `POST /v1/phones/otp {phone_e164: new, biometric_ok: true}`, then `/check` → `pending_parent`. Push `number_change_requested` to parents and the child's device; SMS notice to the old number.
2. Parent: roster shows `pending_phone_last4` → `POST .../phone-change {decision}`. `confirm` cancels open cases, moves the number, restarts the 24 h rule, and sends `number_change_confirmed`.

## 8. Push payloads

Sent by the server via FCM HTTP v1 or APNs, after the database commit. Alert text is generic and localized by the token holder's `users.locale` (`ko`, else `en`).

| `kind` | Recipient | Data keys | Alert body (en / ko) |
| --- | --- | --- | --- |
| `money_request` | The child's device, once, when a case enters `waiting_push` | `kind`, `case_id` | "Family Shield needs you to confirm a request." / "패밀리 쉴드에서 확인이 필요한 요청이 있어요." |
| `number_change_requested` | Every active parent with a token, and the child's device | `kind`, `family_id` | "A phone number in your family is changing. Open the app to review it." / "가족 중 한 명의 전화번호 변경 요청이 있어요. 앱에서 확인해 주세요." |
| `number_change_confirmed` | Same | `kind`, `family_id` | "A phone number in your family was changed. Open the app to see it." / "가족 중 한 명의 전화번호가 변경됐어요. 앱에서 확인해 주세요." |

Title is "Family Shield" / "패밀리 쉴드". FCM message shape: `{"message":{"token","notification":{"title","body"},"data":{"kind":..., "case_id"|"family_id": "<uuid string>"},"android":{"priority":"HIGH","ttl":"90s"}}}` (the 90 s TTL applies to every kind). APNs: `{"aps":{"alert":{"title","body"},"sound":"default"},"kind":...,"case_id"|"family_id":...}` with a 90 s expiration. No yes/no actions in the notification; tapping opens the app. The parent never receives a push about case progress.

## 9. Caps and limits

| Limit | Value | Error |
| --- | --- | --- |
| Cases per parent per child | 5 per rolling 24 h, every stored case counts (decided or not) | 429 `rate_limited` |
| Cases per parent | 10 per rolling 24 h | 429 `rate_limited` |
| OTP starts per member | 5 per rolling 24 h (app OTP and allow page together) | 429 `rate_limited` (allow page: HTML 429) |
| OTP lifetime / attempts | 10 min; 5 misses kill it | 400 `otp_expired` / `otp_wrong` |
| Invite secret | 24 h, single use, re-issue replaces | 400 `invite_expired` / `invite_invalid` |
| Allow link | 72 h, single use, re-issue replaces | HTML 404 |
| Sign-in nonce | 10 min, single use | 401 `invalid_token` |
| Session | 30 days | 401 `unauthorized` |
| One-time call code | 5 min from entering `calling`, single use | (call outcome) |
| Static check code lock | 5 `static_code_mismatch` in 24 h after the code was set; cleared by setting a new code | result `code_locked` |
| `number_recent` window | 24 h after `phone_current_since` (confirm, allow completion, number change) | result `number_recent` |
| Windows | push 90 s, code 180 s, answer 45 s | results `timeout` / `no_answer` |
| Sizes | names ≤ 200; `text` ≤ 8000; audio ≤ 10 MB; transcript stored ≤ 20 000; `id_token` ≤ 8192; sign-in `nonce` ≤ 128; invite `secret` ≤ 64; dev `digits` ≤ 32; push token ≤ 4096; bearer ≤ 512 | 400 `invalid_body` / 413 `audio_too_large`; an over-long bearer is 401 `unauthorized` |
| Family case list | `limit` 1..50, default 20 | 400 `invalid_body` |
| Case text retention | `parent_text` → `""`, `transcript`/`claims` → null 30 days after `decided_at`, by the offline `scripts/purge_case_text` (not the server) | — |

There is no per-IP or per-route rate limit beyond these.

## 10. Local DEV_AUTH backend (Android e2e)

The local backend (`DEV_AUTH=1`, `TIMER_SECONDS=1`, no Twilio, no push, no Anthropic/Cartesia keys, no `PUBLIC_BASE_URL`) behaves like this:

- Sign in with `POST /v1/dev/login`; Apple/Google answer `503 sign_in_unavailable`.
- OTP codes go to `DevOtp`, which logs them server-side; **no route returns them**. To get an active app child, accept the invite with the child's session, then `POST /v1/dev/members/{id}/activate {phone_e164, user_id: <child user_id>}` with the parent's session.
- Calls are only recorded (`"would call +1..."`); the case sits in `calling` until a `/v1/dev/cases/{id}/digits` call or the 180 s window. Drive outcomes: `POST /answer yes` → green; `answer no` → red; digits `*`, then a wrong 4-digit code → yellow `wrong`; or the right one-time code from `call-code`, then `1` within 24 h of activation → yellow `number_recent`.
- A child with a push token stays `waiting_push` for 90 s (no sender: the send counts as transient), then moves to `calling`.
- `call-only` and `allow-link` answer `503 allow_link_unavailable`.
- `transcript`, `claims`, `pattern_id` stay `null`.

## 11. Ambiguities and gaps in the code

- No route removes an active child, leaves a family, signs out, or lists `family_events`.
- `invite_expires_at` and `allow_link_open` stay set after their expiry time; clients must compare times themselves.
- A call-only child that has not completed the allow page can still get an app invite re-issued (`/invite`); nothing guards that mix.
- Case caps are counted per opening parent, so two parents can together open more than 5 cases for one child in 24 h.
- `display_name` from Apple/Google sign-in is optional and is never updated after the first sign-in.
- `502 sms_failed` is returned after the commit: the OTP challenge, call-only number, or allow link is already saved.
- `code_check_slow` exists in the state machine but nothing emits it.
- `opened` is never visible in practice: `POST /v1/cases` either moves the case on in the same transaction or rolls it back.
