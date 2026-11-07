# Family Shield iOS (milestones 9 and 10)

SwiftUI app. The parent flow matches the Android parent app and [docs/API_CONTRACT.md](../docs/API_CONTRACT.md). Logic that does not need UIKit lives in the `FamilyShieldCore` Swift package (Swift 6) so it can be tested with `swift test` on Linux. The app target stays in the Swift 5 language mode so the UIKit and AuthenticationServices calls build without extra concurrency annotations.

The Xcode project is not checked in. [project.yml](project.yml) is an [XcodeGen](https://github.com/yonaskolb/XcodeGen) spec. Generate the project on a Mac; do not hand-edit the generated `FamilyShield.xcodeproj`.

## Placeholders (owner's Apple Developer account)

Nothing here is a real secret. Replace these before a signed run:

| Placeholder | Where | What the owner sets |
| --- | --- | --- |
| `TEAMID` | `DEVELOPMENT_TEAM` in [project.yml](project.yml) | Apple Developer team id |
| `com.familyshield.app` | bundle id in project.yml, and the server | `APPLE_BUNDLE_ID` and `APNS_TOPIC` must be this bundle id |
| Sign in with Apple | `FamilyShield.entitlements` and `FamilyShieldDebug.entitlements` | Enable the capability for this App ID |
| `group.com.familyshield.app` | App Group in the app and Share Extension entitlements | Create the group for `com.familyshield.app` and `com.familyshield.app.share` |
| APNs | `aps-environment` is `development` on Debug and `production` on Release | APNs Auth Key (`.p8`), Key ID, and the team id, as `APNS_*` on the server. The `.p8` stays out of git. |
| API origin | Debug Info.plist `FSApiBase` is `http://127.0.0.1:8000`. Release is empty. | A device on the LAN can set the scheme environment variable `FS_API_BASE` to `http://<mac-ip>:8000`. A store build needs https. |

## Build on a Mac

```bash
brew install xcodegen
cd ios
# Put the real team id in project.yml (DEVELOPMENT_TEAM) before a signed run.
xcodegen generate
cd FamilyShieldCore && swift test && cd ..
xcodebuild -project FamilyShield.xcodeproj -scheme FamilyShield \
  -destination 'platform=iOS Simulator,name=iPhone 16' \
  -configuration Debug \
  CODE_SIGNING_ALLOWED=NO \
  build
xcodebuild -project FamilyShield.xcodeproj -scheme FamilyShield \
  -destination 'platform=iOS Simulator,name=iPhone 16' \
  test
```

`CODE_SIGNING_ALLOWED=NO` only checks that the sources compile. Sign in with Apple and push need a signature, so the simulator run below uses the team.

Debug builds (`DEV_LOGIN`) show developer sign-in, which calls `POST /v1/dev/login`. That path is not compiled into Release. Release also has no `127.0.0.1` default and does not allow cleartext.

## What the parent app does

Sign in with Apple. The app loads a raw nonce from `POST /v1/auth/nonce`, sets the request nonce to the lowercase SHA-256 hex, and posts the raw nonce with the identity token to `POST /v1/auth/apple`. The session token is stored in the Keychain, on this device only, and is not synced. A 401 signs out.

After `GET /v1/me`: create a family, or the parent home. A child account is recognized and told that the child screens are not in this version yet (milestone 11). Creating a family is not offered to a child.

The home screen lists children and recent cases. Add a child and show the invite secret once (copy and share). The copy stays on the local pasteboard for 60 seconds. Re-issue the code. Confirm or reject "{name} wants to join. Number ending {last4}." Confirm or reject a pending number change. Add a `+1` or `+82` number for a child with no app. Verify is enabled only when the child is `active` and `confirmed_at` is set.

Verify opens `POST /v1/cases` with optional pasted text. Nothing is uploaded before that tap. `member_not_callable` and `rate_limited` are errors, not cases. The case screen polls `GET /v1/cases/{id}` about every 3 seconds while it is visible and the colour is open, and stops when the case is decided. Green, red, and yellow use the same sentences as Android, in English and Korean. A red result offers the copyable family warning. The pilot notice names Apple for sign-in and notifications, where Android names Google.

`POST /v1/me/push-token` is implemented (`provider=apns`, `env=sandbox` on Debug and `production` on Release) for a parent. There is no device token in this environment, so registration does nothing until a signed build receives one. The notification text is the server's generic sentence. This milestone does not add a Share Extension or Face ID.

UI tests (`ParentUITests`) launch the app with `--ui-test` and cover an empty family, a child who is not confirmed (Verify disabled), a yellow result, a red result, the Korean red copy, and a shared draft that is not uploaded until Verify. They need the simulator. The same screens are also asserted by `swift test` through `ParentFixtures`, and the voice-note rules (types, 10 MB cap, local copy) are in the package tests.

## Share a voice note (milestone 10)

The Share Extension accepts audio (`public.audio`, including m4a) and plain text, plus Ogg (`org.xiph.ogg`). It copies the file into the App Group `group.com.familyshield.app` and opens `familyshield://share`. `POST /v1/cases` runs only when the parent taps Verify. Text stays JSON. A voice note is multipart with `Content-Length`. A file over 10 MB (10 485 760 bytes) or an empty file is refused on the phone and is not uploaded. The share sheet does not register for movies or generic data, so Family Shield is not offered for every file.

KakaoTalk on a real phone is not a merge gate. The manual check is in [docs/MANUAL_CHECKS.md](../docs/MANUAL_CHECKS.md). If KakaoTalk will not share the voice note, the parent shares the saved file from Files, or pastes the text.
