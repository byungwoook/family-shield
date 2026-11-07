// Resume copy of the milestone 12 workflow used on 2026-11-05 (see docs/CHECKPOINT.md).
// The Backend and Contract phases are already done on claude/m12-android-parent:
// when resuming, delete those two phases and start at Implement.
// Paths like /tmp/claude-0/fsvenv, /tmp/claude-0/e2e/run-backend.sh and
// /opt/android-sdk were this container's; adjust them to the new environment.
export const meta = {
  name: 'android-m12-parent',
  description: 'Backend support, API contract, Android parent app (M12), multi-lens review, adversarial verify, fix, completeness check',
  phases: [
    { title: 'Backend', detail: 'GET /v1/me, case list, sign-in nonce, with pytest' },
    { title: 'Contract', detail: 'write and cross-check docs/API_CONTRACT.md' },
    { title: 'Implement', detail: 'Android parent path, unit + Robolectric UI + e2e tests' },
    { title: 'Review', detail: 'four independent lenses, read-only' },
    { title: 'Verify', detail: 'try to refute each finding' },
    { title: 'Fix', detail: 'apply confirmed findings, rebuild, retest' },
    { title: 'Critic', detail: 'what is still missing vs the M12 spec' },
  ],
}

const REPO = '/home/user/family-shield'
const ENV = `
Environment facts (all agents):
- Repo: ${REPO}, git branch claude/m12-android-parent (already checked out). Do NOT commit, push, or switch branches; the orchestrator commits.
- Python: /tmp/claude-0/fsvenv/bin/python. Backend tests: cd ${REPO} && DATABASE_URL=postgresql://familyshield@localhost:5432/familyshield /tmp/claude-0/fsvenv/bin/python -m pytest -q  (Postgres is already running on localhost:5432; do not start or stop it).
- A local backend (DEV_AUTH=1, TIMER_SECONDS=1) is ALREADY running at http://127.0.0.1:8000 from ${REPO} using database familyshield_e2e. It was started from the code at launch time, so backend code changes are NOT live there until it is restarted: to restart, run \`pkill -f "uvicorn --factory backend.api:boot"\` then start \`/tmp/claude-0/e2e/run-backend.sh > /tmp/claude-0/e2e/backend.log 2>&1 &\` with Bash run_in_background, and poll until POST http://127.0.0.1:8000/v1/dev/login returns 201. If the schema changed, also apply new DDL to familyshield_e2e (it was created from backend/schema.sql; drop and recreate the public schema then call backend.store.apply_schema, via psycopg, if needed).
- Android: project at ${REPO}/android (Gradle wrapper 9.4.1, AGP 9.2.1, Kotlin 2.2.10, Compose BOM 2025.06.01, versions in android/gradle/libs.versions.toml, same toolchain as the owner's Fitrip app). Always: export ANDROID_HOME=/opt/android-sdk LANG=C.UTF-8 LC_ALL=C.UTF-8, and run ./gradlew --no-daemon --max-workers=2 -Dorg.gradle.internal.repository.max.tentatives=12 -Dorg.gradle.internal.repository.initial.backoff=3000 <tasks>. Maven Central sometimes answers 429 through the proxy: wait and retry, never add other repositories. Only ONE Gradle build may run at a time on this 4-CPU machine: before building, wait until \`pgrep -f GradleWrapperMain\` and \`pgrep -f GradleDaemon\` find nothing. Bash foreground commands time out after 10 minutes: run long builds with run_in_background and wait for completion, or wrap with \`timeout\`.
- No emulator (no KVM). UI tests run on the JVM with Robolectric + Compose ui-test. "Runs against the API" is shown by a JVM end-to-end test that drives the app's own API client and repositories against http://127.0.0.1:8000 (DEV_AUTH routes), skipped with Assume when the base URL property is not set.
- Do not read or print .env files. Do not add secrets. There is no Google OAuth client id yet: Google sign-in must build and be wired, but is hidden when BuildConfig.GOOGLE_SERVER_CLIENT_ID is blank; the debug build signs in through the backend's POST /v1/dev/login.
- Product rules live in ${REPO}/docs/PRODUCT_REDESIGN.md (read the sections: What must stay true, Auth onboarding and linking, API, Verification state machine, Parent screen, Copy the app must not regress, Korean and cross-border use, M12). Existing copy sources: ${REPO}/shared/cards.py and ${REPO}/agents/guardian/agent.py (finish / on_code_result / check_timeouts paragraphs). Pattern catalog with en/ko labels: ${REPO}/backend/patterns.json.
`

const IMPL_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    files_changed: { type: 'array', items: { type: 'string' } },
    commands_run: { type: 'array', items: { type: 'string' } },
    tests_passed: { type: 'boolean' },
    test_counts: { type: 'string' },
    e2e_passed: { type: 'boolean' },
    gaps: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'files_changed', 'tests_passed', 'test_counts', 'e2e_passed', 'gaps'],
}
const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          severity: { type: 'string', enum: ['high', 'medium', 'low'] },
          file: { type: 'string' },
          line: { type: 'integer' },
          issue: { type: 'string' },
          evidence: { type: 'string' },
          fix: { type: 'string' },
        },
        required: ['severity', 'file', 'issue', 'evidence', 'fix'],
      },
    },
  },
  required: ['findings'],
}
const VERDICT_SCHEMA = {
  type: 'object',
  properties: { refuted: { type: 'boolean' }, reason: { type: 'string' } },
  required: ['refuted', 'reason'],
}
const CRITIC_SCHEMA = {
  type: 'object',
  properties: {
    gaps: {
      type: 'array',
      items: {
        type: 'object',
        properties: { item: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } },
        required: ['item', 'evidence', 'fix'],
      },
    },
  },
  required: ['gaps'],
}

// ---------------- Backend ----------------
phase('Backend')
const backend = await agent(`${ENV}
Task: add three small backend features the Android parent app needs. Follow the existing style of backend/api.py and backend/store.py (docstrings that state readings, stable {"error": code} bodies, injected clock, store functions that never commit, handlers that commit via _run). Keep the AST test in tests/test_api.py passing (no direct .now()/token_* calls in api.py outside the defaults; put generators in backend modules).

1. GET /v1/me (any session): {"user_id","display_name","locale","memberships":[{"member_id","family_id","family_name","role","status","display_name"}]} for non-removed memberships, ordered by created_at. No phone numbers, no hashes.

2. GET /v1/families/{id}/cases?limit=N (active parent of that family only, else 404 not_found): the most recent cases (default 20, max 50) newest first, each {"id","child_member_id","child_display_name","state","result","color","created_at","decided_at"}. No parent_text, transcript, claims, or codes in the list.

3. Sign-in nonce, so a captured Google or Apple ID token cannot be replayed:
   - POST /v1/auth/nonce (public) returns {"nonce": <server-generated url-safe random, >= 32 chars>, "expires_at"}. Store only keyed_hash("signin_nonce", nonce) (backend/codes.py keyed_hash) in a new table signin_nonces (nonce_hash text primary key, expires_at timestamptz not null, consumed_at timestamptz). TTL 10 minutes. Rate-limit is not required.
   - POST /v1/auth/apple and /v1/auth/google now REQUIRE a "nonce" field (the raw nonce). The client passes sha256_hex(raw_nonce) to Apple / Google as the request nonce, so the ID token's "nonce" claim must equal sha256_hex(raw_nonce) (lowercase hex). Verify in backend/signin.py (IdTokenVerifier.verify gains a required expected_nonce argument; a missing or different nonce claim raises InvalidIdToken("nonce")). The server consumes the nonce atomically (single use, unexpired) in the same transaction as the session insert; unknown/used/expired -> 401 invalid_token, and nothing is written.
   - Update tests/test_signin.py and tests/test_enroll.py so every sign-in passes a server-issued nonce, and add tests: nonce missing from body -> 400 invalid_body; token without nonce claim -> 401; wrong nonce -> 401; reused nonce -> 401; expired nonce -> 401; the nonce row stores no plaintext. Update the store column-set test in tests/test_store.py for the new table if it enumerates tables.
   - Update docs/PRODUCT_REDESIGN.md API table rows for the new routes, briefly.

Add tests for 1 and 2 (authorization, no leaked fields, ordering, limit bounds) in a new tests/test_me.py using the same fixtures style as tests/test_enroll.py (import helpers from test_api). Run the FULL backend suite until it passes; report counts. Then restart the local e2e backend (and apply the new table to familyshield_e2e) so the Android e2e can use the new routes, and confirm with curl that POST /v1/auth/nonce and GET /v1/me (after dev login) work.`, { label: 'backend: /v1/me, case list, nonce', phase: 'Backend', schema: IMPL_SCHEMA, effort: 'high' })
log(`backend: tests_passed=${backend && backend.tests_passed} ${backend && backend.test_counts}`)

// ---------------- Contract ----------------
phase('Contract')
const contract = await agent(`${ENV}
Task: write ${REPO}/docs/API_CONTRACT.md, the client contract both mobile apps build against, derived ONLY from the code (backend/api.py, backend/store.py, backend/enroll.py, backend/signin.py, backend/push.py, backend/allow_page.py) and the tests. For every /v1 route: method, path, who may call it (session role), request body fields with types and limits, success status and every response field with type and meaning, and every error status + {"error": code} the handler can return. Include: auth header format; sign-in sequence with the nonce (raw vs sha256 hex); the parent enrollment sequence (create family -> add child -> invite secret -> child accepts -> child OTP -> parent confirm) and the call-only path; case lifecycle states, result codes, color mapping, gather, timeline step ids that can appear (search the code for every step string), polling guidance (GET /v1/cases/{id} every few seconds until color != open); the parent vs child case views (CHILD_CASE_KEYS); push payload kinds; caps and rate limits. Mark DEV_AUTH-only routes clearly. Do not invent anything the code does not do; where something is ambiguous say so. Keep it in English, compact tables.`, { label: 'contract: write', phase: 'Contract', effort: 'high' })
const contractCheck = await agent(`${ENV}
Task: adversarially verify ${REPO}/docs/API_CONTRACT.md against the code. For every route, field, status code, error code, and step id in the document, find it in backend/*.py; also search the code for any route, error code, or step id the document omits. Fix every discrepancy directly in docs/API_CONTRACT.md (the code is the authority). Return a list of what you corrected as your final text.`, { label: 'contract: verify', phase: 'Contract', effort: 'high' })
log('contract written and cross-checked')

// ---------------- Implement ----------------
phase('Implement')
const impl = await agent(`${ENV}
Task: implement milestone M12, the Android parent path, in ${REPO}/android, against docs/API_CONTRACT.md (read it first; it is authoritative for the API). The scaffold builds already (MainActivity placeholder, BuildConfig API_BASE_URL / DEV_LOGIN / GOOGLE_SERVER_CLIENT_ID, debug-only cleartext for 10.0.2.2/localhost/127.0.0.1). Package com.familyshield.app, Kotlin + Jetpack Compose + Material3, minSdk 26, targetSdk 36. No DI framework: a small app container created in an Application subclass. MVVM: ViewModels exposing StateFlow, repositories over one ApiClient.

Required behaviour (M12 in the design doc, plus the parent screen and copy rules):
- Networking: OkHttp + kotlinx.serialization, base URL from BuildConfig.API_BASE_URL, Bearer session token, reasonable timeouts, error bodies {"error": code} mapped to a typed error; unknown fields ignored. Never log request/response bodies, tokens, or case text.
- Session storage: the session token encrypted at rest with an Android Keystore AES/GCM key (DataStore or SharedPreferences holding only ciphertext + IV); sign-out clears it; a 401 from any call signs the user out.
- Sign-in: Google via Credential Manager (androidx.credentials + googleid GetGoogleIdOption or GetSignInWithGoogleOption) with serverClientId = BuildConfig.GOOGLE_SERVER_CLIENT_ID and nonce = sha256_hex(raw) where raw comes from POST /v1/auth/nonce; then POST /v1/auth/google {id_token, nonce: raw, locale, display_name}. Hide the Google button when the client id is blank. Debug builds (BuildConfig.DEV_LOGIN) also offer a developer sign-in via POST /v1/dev/login (display name + locale). Locale sent is "ko" when the device language is Korean, else "en".
- After sign-in: GET /v1/me. No parent family -> create family screen. A user whose membership is a child gets a placeholder "child app comes in a later update" screen (child path is M14).
- Family screen: GET /v1/families/{id}/members; add a child by display name and show the returned invite secret once with copy + share (Android share sheet) and an explanation that it works once for 24 hours; re-issue invite; pending child cards "{name} wants to join. Number ending {last4}." with Confirm / Reject (POST .../confirm); a pending number change card with Confirm / Reject (POST .../phone-change) when pending_phone_last4 is set; an "add by phone number (no app)" option using POST .../call-only (+1 and +82 only; unsupported_country shown as a clear error). Each child row has a Verify button that is ENABLED ONLY when the child is active and confirmed; otherwise disabled with the reason.
- New case: pick a child (only verifiable ones), optional text (paste the message), Verify -> POST /v1/cases (JSON). member_not_callable and rate_limited shown as errors, not as a case. (Audio sharing is M13: not now.)
- Case screen: poll GET /v1/cases/{id} about every 3 s while color is "open", stop when decided and when the screen is not visible; survive rotation (ViewModel). While open: a prominent "Don't send money yet" message and the timeline (map known step ids to localized strings, unknown ids to a generic line). Claims, when present, under the fixed heading meaning "What the voice note claims (this does NOT prove who it is)". Pattern label from the catalog (copy backend/patterns.json labels into resources) using the green/red rules from the doc. Result card: green / red / yellow with the exact copy from "Copy the app must not regress" for each result code (sent, not_sent, no_number, call_failed, timeout, wrong, no_answer, unreachable, code_locked, number_recent), using the Guardian paragraphs for the yellow cases the doc points at. Red offers a copyable family warning (see shared/cards.py family_alert). The app never says to send money. Also a recent cases list on the family screen from GET /v1/families/{id}/cases.
- All user-visible text in res/values/strings.xml and res/values-ko/strings.xml (natural Korean, same meaning; Korean for the result copy is required). No hard-coded UI strings. Content descriptions for icons. Dark theme follows the system.

Tests (all must pass with testDebugUnitTest):
- JVM unit: ApiClient with MockWebServer (auth header, error mapping, 401 sign-out, parsing of every response type in the contract); result-copy mapping is exhaustive over every result code and color; CaseViewModel polling stops when decided (coroutines-test, virtual time); session crypto round-trip where possible (or isolate the cipher behind an interface tested with a JVM fake + a Robolectric test).
- Robolectric Compose UI tests (the milestone's list): empty family, member not yet confirmed (Verify disabled), yellow result, red result; plus one test that renders a result screen under the ko locale (@Config(qualifiers = "ko")) and finds the Korean copy.
- End-to-end JVM test against the running local backend (system property fs.e2e.base, wired in app/build.gradle.kts from -PfsE2eBase; Assume-skip when blank): uses the app's ApiClient/repositories to dev-login a parent, create a family, add a child, activate it with POST /v1/dev/members/{id}/activate (DEV_AUTH) and set a check code with POST /v1/dev/members/{id}/check-code, open a case, poll until calling, drive the result with POST /v1/dev/cases/{id}/digits (wrong code -> yellow wrong; and in a second case the right code then "2" -> red), and assert the app's view model / result mapping shows yellow and red. Also call /v1/me and the case list.
Run: ./gradlew ... assembleDebug testDebugUnitTest, then ./gradlew ... testDebugUnitTest -PfsE2eBase=http://127.0.0.1:8000 --tests '*E2e*' (adjust the filter to your class name) and make both pass. Also run assembleRelease to make sure the release variant compiles (minify may need keep rules for kotlinx.serialization; add them). Write android/README.md (build, test, e2e, Gradle properties fsApiBase / fsGoogleServerClientId / fsApplicationId, what is not verified on Linux). Report honestly: anything not done goes in gaps.`, { label: 'implement: android parent path', phase: 'Implement', schema: IMPL_SCHEMA, effort: 'xhigh' })
log(`implement: tests_passed=${impl && impl.tests_passed} e2e=${impl && impl.e2e_passed} ${impl && impl.test_counts}`)

// ---------------- Review -> Verify (pipeline) ----------------
const LENSES = [
  { key: 'api', prompt: 'API contract fidelity: every call path, method, body field name and type, query param, response parsing, nullability, error-code handling, auth header, nonce handling (raw vs sha256 hex), 401 handling, polling cadence and stop conditions, against docs/API_CONTRACT.md and backend/api.py. Include mismatches that would only show up at runtime.' },
  { key: 'safety', prompt: 'Safety, privacy, and copy rules from docs/PRODUCT_REDESIGN.md: only the child\'s answer decides green/red; the app never tells the parent to send money; exact result copy per result code (compare with the doc and the Guardian/cards sources); yellow for every non-answer; claims heading wording; pattern label rules under green/red; no codes, full numbers, tokens, or case text in logs, crash messages, notifications, or analytics; session token encrypted at rest with Keystore and cleared on 401/sign-out; release build has no dev login and no cleartext; invite secret shown once; allowBackup off; exported components minimal.' },
  { key: 'ux_i18n', prompt: 'UX states and localization: every screen handles loading, error, empty, and retry; Verify disabled with a reason when the child is not active+confirmed; pending confirm and number-change cards; polling stops when the screen is not visible and survives rotation/process death sensibly; Korean strings exist for EVERY English string and read naturally (check values vs values-ko key sets programmatically by reading both files); no hard-coded strings in Kotlin UI code; accessibility (content descriptions, touch targets, text scaling); dark theme.' },
  { key: 'tests', prompt: 'Tests and build hygiene against the M12 done criteria: Robolectric UI tests for empty family, member not yet confirmed (Verify disabled), yellow result, red result, and a ko-locale render; MockWebServer tests; exhaustive result-copy tests; polling test with virtual time; the end-to-end test against the local backend actually exercises the listed flow and asserts yellow and red; release variant compiles with keep rules; README accuracy. Read the test sources and android/app/build/test-results XML (if present) to see what actually ran.' },
]

const reviewed = await pipeline(
  LENSES,
  lens => agent(`${ENV}
You are reviewing the Android parent app just written in ${REPO}/android (and its README) through ONE lens. Read the code; do NOT run Gradle (another agent may be building) and do not edit files. Lens: ${lens.prompt}
Report only real, specific problems with file and line and concrete evidence (quote the code). No style nits. Return findings (empty list if none).`, { label: `review:${lens.key}`, phase: 'Review', schema: FINDINGS_SCHEMA, effort: 'high' }),
  (review, lens) => parallel(((review && review.findings) || []).map((f, i) => () =>
    agent(`${ENV}
A reviewer claims this problem in ${REPO}/android. Try hard to REFUTE it by reading the code and the contract/doc it cites; do not edit files and do not run Gradle. If the claim is wrong, already handled elsewhere, or not actually a problem for the product rules, set refuted=true. If uncertain after checking, refuted=false only when you found concrete evidence the problem is real.
Claim (${lens.key}, ${f.severity}): ${f.issue}
File: ${f.file}${f.line ? ':' + f.line : ''}
Evidence given: ${f.evidence}
Proposed fix: ${f.fix}`, { label: `verify:${lens.key}#${i + 1}`, phase: 'Verify', schema: VERDICT_SCHEMA })
      .then(v => ({ ...f, lens: lens.key, verdict: v }))))
)
const allFindings = reviewed.filter(Boolean).flat().filter(Boolean)
const confirmed = allFindings.filter(f => f.verdict && !f.verdict.refuted)
log(`review: ${allFindings.length} findings, ${confirmed.length} survived verification`)

// ---------------- Fix ----------------
phase('Fix')
let fix = null
if (confirmed.length) {
  fix = await agent(`${ENV}
Apply these verified review findings to ${REPO}/android (and the backend only if a finding is about it). Keep each fix to what the finding needs. Then rebuild and rerun everything: ./gradlew ... assembleDebug assembleRelease testDebugUnitTest, and the e2e test with -PfsE2eBase=http://127.0.0.1:8000. If backend code changed, rerun the backend pytest suite too. Report which findings you applied and which you skipped with a reason.
Findings (JSON):
${JSON.stringify(confirmed.map(f => ({ lens: f.lens, severity: f.severity, file: f.file, line: f.line, issue: f.issue, fix: f.fix, verifier: f.verdict.reason })), null, 1)}`, { label: 'fix: confirmed findings', phase: 'Fix', schema: IMPL_SCHEMA, effort: 'xhigh' })
  log(`fix: tests_passed=${fix && fix.tests_passed} e2e=${fix && fix.e2e_passed}`)
}

// ---------------- Critic loop ----------------
phase('Critic')
let rounds = 0
let lastCritic = null
while (rounds < 2) {
  rounds += 1
  lastCritic = await agent(`${ENV}
Completeness check for milestone M12 (Android parent path) in ${REPO}/android. Compare the code against: the M12 text and the Parent screen / Copy sections of docs/PRODUCT_REDESIGN.md, docs/API_CONTRACT.md, and the required behaviour list (sign-in incl. nonce, /v1/me routing, family screen with invite secret once, confirm/reject, number-change confirm, call-only add, Verify gating, new case, polling case screen with timeline/claims/pattern/result copy en+ko, family warning on red, recent cases, encrypted session, 401 sign-out, tests: empty family, unconfirmed member Verify disabled, yellow, red, ko render, MockWebServer, polling, e2e). Read the code and the latest test result XML under android/app/build/test-results; do not run Gradle and do not edit. List only concrete gaps (missing or broken), each with evidence and a fix. Empty list if complete.`, { label: `critic round ${rounds}`, phase: 'Critic', schema: CRITIC_SCHEMA, effort: 'high' })
  const gaps = (lastCritic && lastCritic.gaps) || []
  log(`critic round ${rounds}: ${gaps.length} gaps`)
  if (!gaps.length) break
  fix = await agent(`${ENV}
Close these completeness gaps in ${REPO}/android, then rebuild and rerun assembleDebug assembleRelease testDebugUnitTest and the e2e test (-PfsE2eBase=http://127.0.0.1:8000). Report what you did; anything you could not do goes in gaps.
Gaps (JSON): ${JSON.stringify(gaps, null, 1)}`, { label: `close gaps round ${rounds}`, phase: 'Critic', schema: IMPL_SCHEMA, effort: 'xhigh' })
}

return {
  backend,
  contract_check: contractCheck,
  impl,
  findings_total: allFindings.length,
  confirmed: confirmed.map(f => ({ lens: f.lens, severity: f.severity, file: f.file, issue: f.issue })),
  refuted: allFindings.filter(f => f.verdict && f.verdict.refuted).map(f => ({ lens: f.lens, issue: f.issue, why: f.verdict.reason })),
  final_fix: fix,
  critic: lastCritic,
}
