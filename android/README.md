# Family Shield Android (milestones 12, 13, and 14)

Kotlin, Jetpack Compose, Material 3. Package `com.familyshield.app` (override with `-PfsApplicationId`). Toolchain, matching the owner's Fitrip app: Gradle 9.4.1, Android Gradle Plugin 9.2.1, Kotlin 2.2.10, Compose BOM 2025.06.01. minSdk 26, compile/target 36.

The API the app calls is [docs/API_CONTRACT.md](../docs/API_CONTRACT.md).

## Build

```bash
# JDK 17 or 21. ANDROID_HOME must point at an SDK with platform 36.
echo "sdk.dir=$ANDROID_HOME" > local.properties
export LANG=C.UTF-8 LC_ALL=C.UTF-8
./gradlew --no-daemon assembleDebug testDebugUnitTest
./gradlew --no-daemon assembleRelease
```

Gradle properties:

| Property | Meaning |
| --- | --- |
| `fsApiBase` | API origin. Debug defaults to `http://10.0.2.2:8000` (emulator → host). Release has **no** default. |
| `fsGoogleServerClientId` | Google "server" (web) client id, the backend's `GOOGLE_SERVER_CLIENT_ID`. Blank: the Google button is hidden. |
| `fsApplicationId` | Application id. Default `com.familyshield.app`. |
| `fsE2eBase` | When set, `ParentFlowE2eTest` runs against that DEV_AUTH backend. Otherwise the test is skipped. |

A real device uses `-PfsApiBase=http://<your-lan-ip>:8000`. Release builds set `DEV_LOGIN=false`, omit the developer sign-in strings and fields (those live in `src/debug` only), and refuse cleartext (the debug manifest is the only place that allows HTTP, and only for `10.0.2.2`, `localhost`, and `127.0.0.1`).

`assembleRelease` is signed with the debug key so the variant can be built before a Play upload key exists. Replace that `signingConfig` with the owner's keystore before any store upload.

## What the parent app does

Google sign-in (Credential Manager, nonce = SHA-256 hex of `POST /v1/auth/nonce`, raw nonce posted to `POST /v1/auth/google`). Debug builds can also use `POST /v1/dev/login`. After `GET /v1/me`: create a family, or enter an invite code, or the parent home, or the child path.

The home screen lists children and recent cases. Add a child and show the invite secret once (copy and share). Re-issue it. Confirm or reject "{name} wants to join. Number ending {last4}." Confirm or reject a pending number change. Add a `+1` or `+82` number for a child with no app (`unsupported_country` is an error). Verify is enabled only when the child is `active` and `confirmed_at` is set.

Verify opens `POST /v1/cases` with optional pasted text. `member_not_callable` and `rate_limited` are errors, not cases. The case screen polls `GET /v1/cases/{id}` about every 3 seconds while it is visible and the colour is `open`, and stops when the case is decided. Green, red, and yellow use the strings in the product doc (English in `values/`, Korean in `values-ko/`). A red result offers the copyable family warning. The session token is AES-GCM sealed; the preferences file stores only ciphertext. A 401 signs out.

`POST /v1/me/push-token` is implemented (`provider=fcm`, no `env`) for a parent and for a child. This tree has no `google-services.json`, so there is no device token and registration is a no-op. `BiometricPrompt` is the child path, not the parent path.

## What the child app does (milestone 14)

The same binary. A signed-in user with no family can create one or enter the parent's invite code (`POST /v1/invites/accept`). The child then enters a `+1` or `+82` number, the SMS code (or "call me with the code"), and a 4-digit check code twice. The first save sends `biometric_ok: false`. Replacing a code requires `BiometricPrompt` and sends `biometric_ok: true`. An `active` membership skips the phone step, because parent confirm already required a verified number. Until the parent confirms, the child waits.

The question opens from a push (`kind=money_request`, `case_id`). There is no child case list. Yes and No call `POST /v1/cases/{id}/answer` only after `BiometricPrompt` succeeds. Not now posts nothing, so the case stays open and the backend can fall through to the call. While the case is `calling`, the same biometric check calls `GET /v1/cases/{id}/call-code` and shows the 6 digits. That value stays in memory until the child hides it, leaves the question, or the case leaves `calling`. Preferences store two booleans per member (phone verified, check code set), never a code. The notification is the fixed sentence from the API contract: no Yes/No action and no code.

`BiometricPrompt` asks for a strong biometric. On API 30 and later the same prompt can fall back to the device passcode. On API 28–29 the platform cannot combine the two, so a device that has a strong biometric is offered only that. A device with none gets the passcode, so the child is not locked out.

## Share a voice note (milestone 13)

`MainActivity` is `singleTop` and accepts `ACTION_SEND` for `audio/*`, `text/plain`, and `application/ogg`. The file is copied into the app cache and the new-case screen opens with it attached. `POST /v1/cases` runs only when the parent taps Verify. Text alone stays JSON. A voice note is multipart (`child_member_id`, `text`, file `audio`) with `Content-Length` set. The part must be `audio/*` and at most 10 MB (10 485 760 bytes); a larger or empty file is refused on the phone and is not uploaded.

Extensions messengers use are recognized even when the type is generic or slightly wrong: `.m4a` and `audio/x-m4a` become `audio/mp4`, `.aac` and `audio/mp4a-latm` become `audio/aac`, `.ogg` / `application/ogg` become `audio/ogg`, `.opus` becomes `audio/opus`, `.amr` and `audio/amr-wb` become `audio/amr`. `.mp4`, `.webm`, and `.3gp` are accepted only when the sender already marked them as audio, so a video is not uploaded as a voice note. The share sheet does not register for `application/octet-stream` or `video/*`, because Android would then offer Family Shield for every file. A direct intent that does use `application/octet-stream` with an audio-only extension is still accepted.

KakaoTalk on a real phone is not a merge gate. What Kakao's help does and does not say is open question 8 in [docs/PRODUCT_REDESIGN.md](../docs/PRODUCT_REDESIGN.md). The manual check is in [docs/MANUAL_CHECKS.md](../docs/MANUAL_CHECKS.md). If KakaoTalk will not share the voice note, the parent shares the saved file from Files, or pastes the text.

## Tests

```bash
./gradlew testDebugUnitTest
# Against a local DEV_AUTH server (see docs/API_CONTRACT.md §10):
./gradlew testDebugUnitTest -PfsE2eBase=http://127.0.0.1:8000 --tests '*ParentFlowE2eTest'
```

Unit tests cover the API client (MockWebServer, including a multipart voice note with `Content-Length`, and the child routes), result copy, verify gating, polling with virtual time, session encryption, string-table parity, voice-note types and the 10 MB cap, and the share intent (a draft is stored locally and is not uploaded until Verify). Robolectric Compose tests cover an empty family, a child who is not confirmed (Verify disabled), a yellow result, a red result, the Korean red copy, a shared voice note that stays on the draft until Verify is tapped, Not now leaving the question unanswered, the 6-digit code staying off screen until it is revealed, and the check-code reset hiding its fields until biometrics. There is no emulator on this Linux environment (no KVM), so sharing from the Files app and approving BiometricPrompt are not run here.
