# Family Shield Android (parent path, milestone 12)

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

Google sign-in (Credential Manager, nonce = SHA-256 hex of `POST /v1/auth/nonce`, raw nonce posted to `POST /v1/auth/google`). Debug builds can also use `POST /v1/dev/login`. After `GET /v1/me`: create a family, or the parent home, or a placeholder if this account is a child (the child app is milestone 14).

The home screen lists children and recent cases. Add a child and show the invite secret once (copy and share). Re-issue it. Confirm or reject "{name} wants to join. Number ending {last4}." Confirm or reject a pending number change. Add a `+1` or `+82` number for a child with no app (`unsupported_country` is an error). Verify is enabled only when the child is `active` and `confirmed_at` is set.

Verify opens `POST /v1/cases` with optional pasted text. `member_not_callable` and `rate_limited` are errors, not cases. The case screen polls `GET /v1/cases/{id}` about every 3 seconds while it is visible and the colour is `open`, and stops when the case is decided. Green, red, and yellow use the strings in the product doc (English in `values/`, Korean in `values-ko/`). A red result offers the copyable family warning. The session token is AES-GCM sealed; the preferences file stores only ciphertext. A 401 signs out.

`POST /v1/me/push-token` is implemented (`provider=fcm`, no `env`). This tree has no `google-services.json`, so there is no device token and registration is a no-op. `BiometricPrompt` is the child path (milestone 14), not the parent path. Sharing a voice note into the app is milestone 13.

## Tests

```bash
./gradlew testDebugUnitTest
# Against a local DEV_AUTH server (see docs/API_CONTRACT.md §10):
./gradlew testDebugUnitTest -PfsE2eBase=http://127.0.0.1:8000 --tests '*ParentFlowE2eTest'
```

Unit tests cover the API client (MockWebServer), result copy, verify gating, polling with virtual time, session encryption, and string-table parity. Robolectric Compose tests cover an empty family, a child who is not confirmed (Verify disabled), a yellow result, a red result, and the Korean red copy. There is no emulator on this Linux environment (no KVM), so nothing here is a device UI test.
