# 체크포인트: 어디까지 했고, 어떻게 이어가는지

마지막 갱신: 2026-11-07. 백엔드 v1과 Android 부모·공유·자녀 앱(M12–M14)은 main에 병합돼 있다. 이 브랜치는 M11 iOS 자녀 화면(Face ID)이고, M10 공유 확장 위에 쌓여 있다. 시뮬레이터와 기기 확인, APNs 키는 아직 없다. 이 파일만 읽으면 바로 시작할 수 있게 쓴다.
설계의 권위는 [PRODUCT_REDESIGN.md](PRODUCT_REDESIGN.md), API의 권위는 코드와 그것을 옮긴 [API_CONTRACT.md](API_CONTRACT.md)다.

## 1. 한 줄 요약

백엔드는 v1 범위(M1–M8, M15, M16)가 main에 병합됐다. Android 부모 앱(M12), 공유 인텐트(M13), 자녀 화면(M14)도 main에 있다. M9·M10은 아래 브랜치에 있다. 이 브랜치는 거기에 M11 자녀 화면을 더한다. 초대 수락, +1/+82 번호와 문자 코드, 확인 번호 두 번, Face ID(기기 암호로 넘어감) 뒤 예/아니요, 통화 중 6자리, 확인 번호 재설정이다. 나중에(Not now)는 답을 올리지 않는다. 알림에는 예/아니요도 코드도 없다. `swift test`는 **33 passed**. 백엔드 경로는 추가하지 않았다. 백엔드는 `PGTZ=UTC`로 **682 passed, 1 skipped**(이 환경에는 Postgres가 없어 pytest를 다시 돌리지는 못했다. 백엔드 파일은 그대로다). Xcode 시뮬레이터와 Face ID 기기 확인, APNs 키는 남아 있다.

## 2. PR 스택 (포크 `byungwoook/family-shield`, 원본에는 PR 없음)

#5~#15는 main에 병합됐다. M9는 PR #16(`cursor/m9-ios-parent-4516`, base main). M10은 PR #17(`cursor/m10-ios-share-4516`, base M9). 이 브랜치(`cursor/m11-ios-child-4516`)는 M10 위에 M11만 더한다. GitHub는 Origin 스택을 지원하지 않아서, 각 PR의 베이스 브랜치로 쌓는다. diff는 그 마일스톤만 보인다.

| PR | 브랜치 | 내용 | 상태 |
|---|---|---|---|
| #5~#12 | (각 기능 브랜치) | M4~M8, M15, M16 | main에 병합 |
| #13 | `claude/m12-android-parent` | M12 Android 부모 앱 | main에 병합. 에뮬레이터·FCM 기기 토큰은 여전히 수동 |
| #14 | `cursor/m13-android-share-4d8a` | M13 Android 공유 인텐트 | main에 병합. 에뮬레이터 파일 공유와 카카오톡 수동 확인은 남음 |
| #15 | `cursor/m14-android-child-308a` | M14 Android 자녀 화면 | main에 병합. 에뮬레이터 생체 인증과 FCM 기기 토큰은 남음 |
| #16 | `cursor/m9-ios-parent-4516` | M9 iOS 부모 화면 | main 기준. 시뮬레이터 수동 확인과 APNs 기기 토큰은 남음 |
| #17 | `cursor/m10-ios-share-4516` | M10 iOS 공유 확장 | M9 위에 쌓음. 시뮬레이터 파일 공유와 카카오톡은 남음 |
| — | `cursor/m11-ios-child-4516` | M11 iOS 자녀 화면 | M10 위에 쌓음. Face ID와 APNs 기기 토큰은 남음 |
| — | `wip/m12-android-partial` | 컴파일된 적 없는 초안. **병합 금지, 참고만** | 보관 |

`claude/m12-android-parent`에 들어간 것:
- 백엔드: `GET /v1/me`, `GET /v1/families/{id}/cases`, 로그인 nonce(`POST /v1/auth/nonce`, Apple/Google 로그인에 nonce 필수). `signin_nonces` 테이블 추가.
- `docs/API_CONTRACT.md`: 코드에서 옮기고 경로별로 코드·실행 중인 백엔드와 대조해 고친 클라이언트 계약.
- `android/`: Gradle 9.4.1 / AGP 9.2.1 / Kotlin 2.2.10 / Compose BOM 2025.06.01 골격(Fitrip 앱과 같은 툴체인). 화면은 자리표시 하나뿐.
- #12의 보안 수정(운영에서 FastAPI 문서 경로 끄기)까지 병합해 둠.
- 테스트: 백엔드 전체 **682 passed, 1 skipped**(`PGTZ=UTC`, 2026-11-07 이 환경에서 재확인. 건너뛴 1개는 안내 음성 mp3가 아직 없어서).
- Android M12: `assembleDebug`, `assembleRelease`, `testDebugUnitTest` 통과. 그때 `-PfsE2eBase` 없이 단위 테스트는 **31 passed, 1 skipped**(e2e). DEV_AUTH 서버를 붙이면 e2e 1개도 통과(**32 passed**). 툴체인은 그대로다. Gradle 래퍼 `networkTimeout`만 10초에서 120초로 늘렸다.
- Android M13 (PR #14, 2026-11-07): 같은 세 가지를 다시 통과. 단위 테스트는 **56 passed, 1 skipped**(건너뛴 1개는 여전히 e2e). 릴리스 APK에 `10.0.2.2`와 개발자 로그인 문구는 없다. 백엔드는 `PGTZ=UTC`로 **682 passed, 1 skipped**.
- Android M14 (이 브랜치, 2026-11-07): `assembleDebug`, `assembleRelease`, `testDebugUnitTest` **77 passed, 1 skipped**. 릴리스 APK에 `10.0.2.2`와 개발자 로그인 문구는 없다. 백엔드는 Python 3.12와 로컬 Postgres 16에서 `PGTZ=UTC`로 **682 passed, 1 skipped**.

### 2026-11-06 로컬(macOS) 확인 결과
- 코드 변경 없음. 이 커밋은 문서만 고친다.
- 백엔드: `PGTZ=UTC`로 돌리면 **682 passed, 1 skipped**(클라우드와 같음). `PGTZ` 없이 Postgres 서버 시간대가 UTC가 아니면 `tests/test_me.py` 2개가 실패한다(아래 4절 "코드에서 발견한 것").
- 개발 서버(DEV_AUTH)를 띄워 `/docs` 200, `POST /v1/auth/nonce` 201 확인.
- Android: 그날은 `local.properties`만 만들고 Gradle을 실행하지 않았다. 그 다음 Linux에서 빌드와 테스트를 확인했다(2절, 5.3).

## 3. 마일스톤 현황

| 마일스톤 | 상태 |
|---|---|
| M1–M8, M15, M16 (백엔드) | 완료, PR #2–#12 |
| M12 Android 부모 화면 | main (PR #13). JVM 테스트와 DEV_AUTH 스모크 통과. 에뮬레이터 수동 확인과 FCM 기기 토큰은 남음 |
| M13 Android 공유 인텐트 | main (PR #14). `audio/*`·`text/plain`·`application/ogg` 공유가 초안이 되고, 확인을 눌러야 multipart로 올라간다. 10MB(10 485 760바이트)는 폰에서 거절. 에뮬레이터에서 파일 앱으로 공유하는 확인과 카카오톡 수동 확인은 남음 |
| M14 Android 자녀 화면 | main (PR #15). JVM 77 passed, 1 skipped. 에뮬레이터 생체 인증과 FCM 기기 토큰은 남음. 백엔드 경로는 추가하지 않음 |
| M9 iOS 부모 화면 | PR #16. SwiftUI + XcodeGen. `swift test`는 M10에서 27로 늘었다. 시뮬레이터 UI 테스트와 Apple 로그인 기기 확인은 남음 |
| M10 iOS 공유 확장 | PR #17. `public.audio`·글·Ogg. 확인 전에 업로드하지 않음. 시뮬레이터 파일 앱 공유와 카카오톡은 남음 |
| M11 iOS 자녀 화면 | **이 브랜치.** 초대·번호·OTP·확인 번호·Face ID 답변·통화 코드·재설정. `swift test` 33 passed. 기기 Face ID와 APNs 키는 남음. 백엔드 경로는 추가하지 않음 |
| M17 발신 번호 표시(iOS/Android) | 시작 전 |
| M18 해커톤 에이전트 코드 제거 | 마지막에. 앱 자녀 화면이 쓸 만해진 뒤 |
| M19 Safe Wallet | v1 이후, 법률 검토 후 |

## 4. 열린 항목

### 키·계정이 있어야 하는 것 (사용자 결정: 마지막에)
전체 절차는 [MANUAL_CHECKS.md](MANUAL_CHECKS.md).
- **Cartesia** `CARTESIA_API_KEY`, 한국어 목소리 `CARTESIA_VOICE_ID_KO`: 안내 mp3 12개 생성(`python -m scripts.render_prompts`) 후 직접 듣고 커밋. 없으면 운영 부팅이 거부된다.
- **Twilio**: +1/+82 SMS·음성 OTP 도착, 실제 확인 전화, 앱 없는 자녀 링크. `scripts/twilio_smoke.py`.
- **Anthropic** `ANTHROPIC_API_KEY`: 실제 주장 추출 확인.
- **Apple Developer**(번들 ID, APNs 키), **Google/Firebase**(Android 패키지명, Google 로그인 서버 클라이언트 ID, FCM 서비스 계정).
- 호스팅: `PUBLIC_BASE_URL`, Postgres 위치(설계 문서 열린 질문 7).

### PR #5~#12
- main에 병합됐다. 이 브랜치도 그 main을 병합해 두었다.

### 코드에서 발견한 것
- ~~운영에서 FastAPI 기본 문서 경로가 열려 있다~~ → **고침** (#12, `Stop serving the generated API docs outside DEV_AUTH`).
- [API_CONTRACT.md §11](API_CONTRACT.md)의 목록: 활성 자녀 제거·가족 탈퇴·로그아웃·가족 이벤트 조회 경로 없음, 만료 시각이 지나도 `invite_expires_at`/`allow_link_open`이 남음, 앱 없는 자녀에게 앱 초대를 다시 발급할 수 있음, `502 sms_failed`가 커밋 뒤에 나감, `code_check_slow`를 내보내는 곳 없음.
- **API 시각이 DB 세션 시간대를 따른다.** `_iso()`(`backend/api.py`)가 Postgres가 돌려준 `timestamptz`를 그대로 `isoformat()`해서, 서버 시간대가 `America/Chicago`면 `-06:00`으로 나간다. 시각 자체는 맞지만 계약 예시(`+00:00`)와 테스트는 UTC를 가정한다. 고치지 않았다. 연결 시 세션을 UTC로 고정(`options="-c TimeZone=UTC"`)하거나 `_iso()`에서 UTC로 바꾸는 방안 중 결정 필요. 그 전까지는 `PGTZ=UTC`를 붙여 테스트·서버를 돌린다.

### 정해 둔 기본값 (바꾸려면 말하면 됨)
- Android 패키지명 `com.familyshield.app`(`-PfsApplicationId`로 변경 가능). iOS 번들 ID도 같은 값이다. 서버 `APPLE_BUNDLE_ID`와 `APNS_TOPIC`이 이 값이어야 한다.
- iOS 서명 팀 ID는 `ios/project.yml`의 `TEAMID` 자리표시자다. 실제 팀 ID와 APNs `.p8`은 넣지 않는다.
- 자녀당 케이스 상한은 **부모 1명 기준** 하루 5건, 부모당 10건.
- 앱 없는 자녀 링크 유효기간 72시간, 초대 코드 24시간.
- Claude 분석 기본 모델 `claude-sonnet-5-5`(`CLAUDE_MODEL`), 서버 측 거절 폴백 켬.

## 5. 로컬에서 이어가기

### 5.1 코드 받기
```bash
git clone https://github.com/byungwoook/family-shield.git && cd family-shield
git checkout cursor/m11-ios-child-4516   # M11. 베이스는 M10 (cursor/m10-ios-share-4516)
```

### 5.2 백엔드 (Python 3.13, Postgres)
```bash
python3 -m venv venv && venv/bin/pip install -r requirements.txt
docker compose up -d                       # 로컬 Postgres (docker-compose.yml)
venv/bin/python -m pytest -q               # 682 passed, 1 skipped 가 기준
```
테스트는 `DATABASE_URL`이 없으면 `postgresql://familyshield:familyshield@127.0.0.1:5432/familyshield`를 쓴다.

Docker가 없는 Mac(Homebrew Postgres)에서 한 방법:
```bash
uv venv --python 3.13 venv && uv pip install --python venv/bin/python -r requirements.txt   # 시스템 python이 3.14여도 됨
brew services start postgresql@18
psql -h 127.0.0.1 -d postgres -c "create role familyshield login password 'familyshield' createdb;"
createdb -h 127.0.0.1 -O familyshield familyshield
createdb -h 127.0.0.1 -O familyshield familyshield_dev
PGTZ=UTC venv/bin/python -m pytest -q      # PGTZ=UTC 필수 (4절 시간대 항목)
```
아래 개발 서버 명령에도 앞에 `PGTZ=UTC`를 붙인다.

앱을 붙여 볼 로컬 서버(DEV_AUTH, 실제 SMS·전화·푸시 없음):
```bash
createdb -h 127.0.0.1 -U familyshield familyshield_dev   # 또는 docker exec 로 생성
venv/bin/python -c "import psycopg; from backend.store import apply_schema; \
c=psycopg.connect('postgresql://familyshield:familyshield@127.0.0.1:5432/familyshield_dev', autocommit=True); apply_schema(c)"
ENV=development DEV_AUTH=1 TIMER_SECONDS=1 \
DATABASE_URL=postgresql://familyshield:familyshield@127.0.0.1:5432/familyshield_dev \
CODE_PEPPER=dev-pepper-0123456789 OTP_DERIVATION_KEY=dev-derivation-0123456789 \
venv/bin/uvicorn --factory backend.api:boot --host 0.0.0.0 --port 8000
```
- 개발 모드에서는 `http://127.0.0.1:8000/docs`에서 API를 바로 볼 수 있다.
- SMS 인증번호는 응답으로 오지 않고 서버 로그(`DevOtp`)에 찍힌다.
- 로컬 서버 동작 정리는 [API_CONTRACT.md §10](API_CONTRACT.md).

### 5.3 Android (M12부터)
- Android Studio를 설치하고 `android/` 폴더를 연다. SDK 36, JDK 17 이상.
- 빌드·테스트: `cd android && ./gradlew assembleDebug testDebugUnitTest`.
- 먼저 `android/local.properties`에 `sdk.dir=$HOME/Library/Android/sdk`(실제 절대 경로로)를 쓴다. gitignore 대상이라 기기마다 만든다.
- JDK: 기본 `java`가 너무 새 버전(예: JDK 27)이면 Gradle 9.4.1이 못 돌 수 있다. Android Studio에 들어 있는 JDK 21을 쓴다:
  `export JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"`
- 에뮬레이터는 호스트의 백엔드를 `http://10.0.2.2:8000`으로 본다(디버그 빌드 기본값). 실제 기기는 `-PfsApiBase=http://<맥 IP>:8000`.
- 디버그 빌드는 Google 로그인 대신 백엔드의 개발용 로그인(`POST /v1/dev/login`)을 쓴다. Google 클라이언트 ID가 생기면 `-PfsGoogleServerClientId=...`.
- 클라우드 환경에서 겪은 문제(프록시 429, UTF-8 로캘, KVM 없음)는 로컬에서는 보통 생기지 않는다. 로캘 오류가 나면 `export LANG=en_US.UTF-8`.
- 2026-11-07 이 Linux 환경에서 `assembleDebug`, `assembleRelease`, `testDebugUnitTest`를 끝까지 확인했다. JDK 21, SDK 36, build-tools 36.0.0. 릴리스 APK에는 `10.0.2.2`와 개발자 로그인 문구가 없다. 릴리스 서명은 아직 디버그 키다. 스토어에 올리기 전에 소유자 키스토어로 바꾼다.

### 5.4 M12에서 된 것과 남은 것
된 것 (이 브랜치, `android/README.md`):
- Google 로그인(Credential Manager, nonce는 SHA-256 hex, 서버에는 raw). 클라이언트 ID가 비면 버튼이 숨는다. 디버그만 `POST /v1/dev/login`.
- 가족 만들기, 자녀 명단, 초대 코드 한 번 표시(복사·공유), 재발급, 가입 승인/거절, 번호 변경 승인/거절, 앱 없는 자녀(+1/+82, `unsupported_country`는 오류).
- 확인 버튼은 `active`이고 `confirmed_at`이 있을 때만. 텍스트로 케이스를 연다. `member_not_callable`과 `rate_limited`는 케이스가 아니라 오류.
- 케이스 화면은 보이는 동안 약 3초마다 폴링하고, 결정되면 멈춘다. 초록/빨강/노랑 문구(en, ko), 빨강은 가족 경고 복사.
- 세션 토큰은 AES-GCM. 401이면 로그아웃. `POST /v1/me/push-token`(fcm)은 구현돼 있다.
- 테스트: API 클라이언트, 문구 매핑, 폴링, 세션 암호, 문자열 표, Robolectric(빈 가족, 확인 전 자녀, 노랑, 빨강, 한국어). DEV_AUTH e2e는 잘못된 코드 → 노랑 `wrong`, 맞는 코드 다음 2 → 빨강 `not_sent`.

남은 것 (그래서 #13은 초안):
- 에뮬레이터/실기기에서 손으로 누르는 확인. 이 환경에는 KVM이 없다.
- FCM 기기 토큰. `google-services.json`이 없어 등록 호출은 토큰이 없으면 아무것도 하지 않는다.
- `BiometricPrompt`는 자녀 화면(M14)에 있다. 부모 화면에는 없다.
- 릴리스 서명은 디버그 키다.

### 5.5 M13에서 된 것과 남은 것
된 것 (`android/README.md`, main의 M13):
- `ACTION_SEND` `audio/*`, `text/plain`, `application/ogg`. 액티비티는 `singleTop`이라 앱이 켜진 채 공유해도 같은 화면이 갱신된다.
- 음성은 앱 캐시에 복사되고 초안 화면에 붙는다. 확인을 누르기 전에는 `POST /v1/cases`를 호출하지 않는다. 글만 있으면 기존처럼 JSON, 음성이 있으면 multipart이고 `Content-Length`가 있다.
- m4a, aac, ogg/opus, amr(및 amr-wb)를 `audio/*`로 맞춰 보낸다. 10MB를 넘거나 빈 파일은 올리기 전에 거절한다. `.mp4`·`.webm`·`.3gp`는 보낸 쪽이 이미 audio라고 한 경우만 받는다.
- 공유 시트에 `application/octet-stream`과 `video/*`는 넣지 않았다. 확장자만으로 모든 제공자를 거를 수 없고, 동영상이 음성으로 올라가면 안 된다.
- 테스트: 형식 매핑, 10MB 한계, 인텐트 복사, 확인 전에 업로드하지 않음, multipart `Content-Length`, 초안 화면. **56 passed, 1 skipped**.

남은 것:
- 에뮬레이터/실기기에서 파일 앱으로 음성을 공유해 초안이 열리는지. 이 환경에는 KVM이 없다.
- 카카오톡이 받은 음성메시지를 다른 앱에 오디오 파일로 넘기는지. 공식 도움말만 읽었고, 기기로 확인하지 못했다. 안 되면 파일 앱으로 공유하거나 글을 붙여 넣는다. [PRODUCT_REDESIGN.md](PRODUCT_REDESIGN.md) 열린 질문 8, [MANUAL_CHECKS.md](MANUAL_CHECKS.md).
- iOS 공유 확장(M10)은 이 마일스톤이 아니다. 만들지 않았다.
- M12에서 남은 에뮬레이터 수동 확인, FCM 기기 토큰, 릴리스 서명.

### 5.6 M14에서 된 것과 남은 것
된 것 (`android/README.md`, 이 브랜치):
- 가족이 없는 계정은 가족을 만들거나 초대 코드를 넣는다. `POST /v1/invites/accept`.
- 자녀는 +1/+82 번호를 넣고 문자 코드(또는 전화 코드)를 확인한 뒤, 4자리 확인 번호를 두 번 넣어 저장한다. 처음 정할 때는 `biometric_ok: false`. 이미 번호가 있으면 `phone_already_set`으로 넘어가고, 이미 확인 번호가 있으면 `biometric_required`로 넘어가며 그 자리에서 바꾸지 않는다.
- `active`인 멤버십은 번호 단계를 건너뛴다. 보호자 승인은 번호 인증을 이미 요구하기 때문이다.
- 보호자 승인 전에는 대기 화면. 승인 뒤 홈. 푸시(`kind=money_request`, `case_id`)가 질문을 연다. 자녀 케이스 목록 API는 없다.
- 예/아니요는 `BiometricPrompt` 성공 뒤에만 `POST /v1/cases/{id}/answer`. 나중에(Not now)는 올리지 않아서 케이스가 열린 채로 남고, 90초 뒤 전화로 넘어갈 수 있다.
- 상태가 `calling`일 때만, 생체 인증 뒤에 `GET /v1/cases/{id}/call-code`. 6자리는 화면 메모리에만 있고, 숨기거나 닫거나 통화가 끝나면 지운다. 설정에는 불리언(번호 인증함, 확인 번호 있음)만 저장한다.
- 확인 번호를 바꿀 때도 생체 인증이 먼저다. 그다음 `biometric_ok: true`.
- 알림 문장은 계약과 같다. 예/아니요 액션이 없고 코드가 없다. `google-services.json`이 없어 FCM 토큰 등록은 M12와 같이 토큰이 없으면 아무것도 하지 않는다.
- 테스트: 규칙, API 본문, 나중에가 답을 올리지 않음, 코드가 저장되지 않음, 재설정은 생체 인증 뒤, 알림에 액션·코드 없음, 질문 화면. **77 passed, 1 skipped**. `assembleDebug`, `assembleRelease` 통과. 릴리스 APK에 `10.0.2.2`와 개발자 로그인 문구는 없다.
- 백엔드는 고치지 않았다. `PGTZ=UTC`로 **682 passed, 1 skipped**. `docs/API_CONTRACT.md`도 그대로다.
- iOS(M9–M11)는 이 마일스톤이 아니다. 이 Linux 환경에는 Xcode가 없어 iOS는 빌드하지 않았다.

남은 것:
- 에뮬레이터/실기기에서 지문 또는 얼굴로 질문에 답하고, 통화 중 6자리를 보는 확인. 이 환경에는 KVM이 없다. [MANUAL_CHECKS.md](MANUAL_CHECKS.md) 8절.
- FCM 기기 토큰. `google-services.json`이 없다.
- M12·M13에서 남은 에뮬레이터 수동 확인, 카카오톡, 릴리스 서명(아직 디버그 키).

소유자가 볼 결정:
- API 30 이상에서는 강한 생체 인증과 기기 비밀번호를 한 프롬프트에 넣었다. 28–29는 둘을 같이 못 쓰므로, 강한 생체가 있으면 그것만 쓴다. 강한 생체가 없으면 비밀번호로 넘어간다.
- 자녀 수신함 API는 추가하지 않았다. 질문 화면은 푸시의 `case_id`로 연다.
- 재설치하면 번호 화면이 다시 나온다. 서버가 `phone_already_set` 또는 `biometric_required`를 주면 코드를 바꾸지 않고 다음 단계로 간다. `GET /v1/me`에는 번호·확인 번호 여부가 없다.

### 5.7 M9에서 된 것과 남은 것
된 것 (`ios/README.md`, 이 브랜치):
- Xcode 프로젝트는 커밋하지 않는다. `ios/project.yml`(XcodeGen)이 원본이다. Mac에서 `xcodegen generate`로 만든다.
- UIKit이 필요 없는 로직은 `ios/FamilyShieldCore`다. 이 Linux에서 Swift 6.2.1로 `swift test` **18 passed**. API 모델, +1/+82 번호, 4자리 확인 번호 모양, 결과 문구(en/ko), 확인 버튼 조건, 폴링이 결정되거나 401이면 멈추는 규칙.
- 화면은 SwiftUI. Apple 로그인 버튼은 시스템 버튼이다. nonce는 `POST /v1/auth/nonce`의 raw를 SHA-256 hex로 요청에 넣고, 서버에는 raw를 보낸다. 세션 토큰은 이 기기 키체인에만 둔다.
- 디버그 빌드만 개발자 로그인(`POST /v1/dev/login`)과 `http://127.0.0.1:8000`이 있다. 릴리스 Info.plist에는 그 주소가 없고, 개발자 로그인 문구는 `#if DEV_LOGIN` 안에만 있다.
- 부모 화면은 Android M12와 같다. 가족 만들기, 초대 코드 한 번(복사·공유, 붙여넣기는 60초 후 로컬에서 사라짐), 재발급, 가입 승인/거절, 번호 변경 승인/거절, 앱 없는 자녀(+1/+82), 텍스트로 케이스, 약 3초 폴링, 초록/빨강/노랑, 빨강은 가족 경고 복사. 확인은 `active`이고 `confirmed_at`이 있을 때만.
- 자녀로 로그인한 계정은 가족을 만들 수 없다. 자녀 화면은 M11까지 자리표시만 보여 준다.
- `POST /v1/me/push-token`(`apns`, 디버그는 `sandbox`, 릴리스는 `production`)은 토큰이 있을 때만 호출한다. 이 환경에는 토큰이 없다.
- UI 테스트 소스(`ParentUITests`)는 빈 가족, 승인 전 자녀(확인 버튼 비활성), 노랑, 빨강, 한국어 빨강을 시뮬레이터에서 연다. 여기서는 실행하지 못했다. 같은 화면 상태는 `ParentFixtures`로 `swift test`가 확인한다.
- 백엔드는 고치지 않았다. `docs/API_CONTRACT.md`도 그대로다.
- Info.plist와 entitlements는 Python `plistlib`으로 XML을 읽었다. 릴리스 plist에 `127.0.0.1`은 없다. `plutil`은 이 Linux에 없다.

남은 것:
- Mac에서 시뮬레이터로 빌드·UI 테스트·개발자 로그인 흐름. [MANUAL_CHECKS.md](MANUAL_CHECKS.md) 9절. 이 환경에는 Xcode가 없다.
- Sign in with Apple 실제 로그인, APNs 키, 팀 ID. 자리표시자만 있다.
- M10 공유 확장, M11 Face ID 자녀 화면.

소유자가 볼 결정:
- 번들 ID를 Android 패키지명과 같은 `com.familyshield.app`로 뒀다. `APPLE_BUNDLE_ID`와 `APNS_TOPIC`을 이 값으로 맞춘다.
- 팀 ID는 `TEAMID`다. 서명된 실행 전에 `ios/project.yml`에서 바꾼다.
- 초대 코드 복사는 로컬 클립보드에 60초만 둔다.
- 시범 안내 문구는 Android가 Google이라고 쓴 자리에 Apple을 넣었다.

### 5.8 M10에서 된 것과 남은 것
된 것 (`ios/README.md`, 이 브랜치):
- 공유 확장 `com.familyshield.app.share`. 활성화 규칙은 `public.audio`, `public.plain-text`, `org.xiph.ogg`다. 동영상과 일반 파일은 공유 시트에 넣지 않았다.
- 파일은 App Group `group.com.familyshield.app`의 `share-drafts`에 복사되고, `familyshield://share`로 부모 앱의 초안이 열린다. 확인을 누르기 전에는 `POST /v1/cases`를 호출하지 않는다. 글만 있으면 JSON, 음성이 있으면 multipart이고 `Content-Length`가 있다.
- 10MB를 넘거나 빈 파일은 복사 중에 끊고 올리지 않는다. 확장자는 Android와 같이 m4a, aac, ogg, opus, amr, caf를 오디오로 맞춘다. `.mp4`는 보낸 쪽이 이미 audio라고 한 경우만 받는다.
- 로그인 전·가족 만들기 전·자녀 계정에는 대기 문구가 있고, 지우면 로컬 파일이 삭제된다.
- 테스트: 형식 매핑, 10MB 한계, 스트리밍 복사가 한도를 넘기면 파일을 지움, 글 공유는 파일을 만들지 않음, multipart `Content-Length`. **27 passed**.
- 백엔드는 고치지 않았다. `docs/API_CONTRACT.md`도 그대로다.
- 공유 확장 Info.plist는 Python `plistlib`으로 읽었다. 활성화 규칙 문자열이 들어 있다.

남은 것:
- Mac에서 파일 앱으로 음성을 공유해 초안이 열리는지. [MANUAL_CHECKS.md](MANUAL_CHECKS.md) 10절. 이 환경에는 Xcode가 없다.
- App Group은 개발자 계정에서 만들어야 한다. 자리표시자 `group.com.familyshield.app`.
- 카카오톡이 받은 음성메시지를 다른 앱에 오디오로 넘기는지. 안 되면 파일 앱으로 공유하거나 글을 붙여 넣는다.
- M9에서 남은 시뮬레이터 수동 확인, Apple 로그인, APNs.

소유자가 볼 결정:
- 공유 확장이 앱을 여는 주소는 `familyshield://share`다. iOS 17에서 공유 확장이 호스트를 직접 못 열면, 같은 응답자 사슬로 `openURL:`을 한 번 더 시도한다.
- 그룹 컨테이너가 없으면 확장은 안내 문장을 보여주고 올리지 않는다.

### 5.9 M11에서 된 것과 남은 것
된 것 (`ios/README.md`, 이 브랜치):
- 가족이 없는 계정은 가족을 만들거나 초대 코드를 넣는다. `POST /v1/invites/accept`.
- 자녀는 +1/+82 번호를 넣고 문자 코드(또는 전화 코드)를 확인한 뒤, 4자리 확인 번호를 두 번 넣어 저장한다. 처음 정할 때는 `biometric_ok: false`. 이미 번호가 있으면 `phone_already_set`으로 넘어가고, 이미 확인 번호가 있으면 `biometric_required`로 넘어가며 그 자리에서 바꾸지 않는다.
- `active`인 멤버십은 번호 단계를 건너뛴다.
- 예/아니요와 6자리 통화 코드, 확인 번호 재설정은 `LAContext`의 `deviceOwnerAuthentication` 성공 뒤에만 한다. Face ID가 안 되면 기기 암호로 넘어가서 자녀가 갇히지 않는다.
- 나중에(Not now)는 `POST /v1/cases/{id}/answer`를 호출하지 않는다. 케이스는 열린 채로 남아서 90초 뒤 전화로 넘어갈 수 있다.
- 6자리는 화면 메모리에만 있고, 숨기거나 통화가 `calling`을 벗어나면 지운다. 설정에는 불리언(번호 인증함, 확인 번호 있음)만 저장한다. 코드는 저장하지 않는다.
- 알림은 서버 문장 그대로다. 예/아니요 액션을 등록하지 않는다. 페이로드에 코드가 있어도 탭 정보에는 `kind`와 `case_id`만 남긴다.
- 재설정 JSON은 Face ID 성공 뒤에만 만들고, `biometric_ok: true`와 새 코드만 담는다. 이전 코드는 본문에 없다.
- 테스트: 위 규칙. **33 passed**. 백엔드는 고치지 않았다. `docs/API_CONTRACT.md`도 그대로다.
- `NSFaceIDUsageDescription`을 Info.plist에 넣었다. Python `plistlib`으로 확인했다.

남은 것:
- Mac의 시뮬레이터(Features > Face ID > Enrolled)와 실기기에서 질문에 답하고, 통화 중 6자리를 보는 확인. [MANUAL_CHECKS.md](MANUAL_CHECKS.md) 11절. 이 환경에는 Xcode가 없다.
- APNs 키(`.p8`), Key ID, 팀 ID. 자리표시자만 있다. 디버그는 `env=sandbox`, 릴리스는 `production`.
- M9·M10에서 남은 시뮬레이터 수동 확인, 카카오톡, App Group을 개발자 계정에 만들기.

소유자가 볼 결정:
- Android 문구가 지문이라고 한 생체 안내를, iOS에서는 Face ID와 기기 암호로 바꿨다. 질문·결과·알림 문장은 Android와 같다.
- 자녀 수신함 API는 추가하지 않았다. 질문 화면은 푸시의 `case_id`로 연다.
- 재설치하면 번호 화면이 다시 나온다. 서버가 `phone_already_set` 또는 `biometric_required`를 주면 코드를 바꾸지 않고 다음 단계로 간다.

### 5.10 그다음
1. M17 발신 번호 표시.
2. 키가 필요한 수동 확인([MANUAL_CHECKS.md](MANUAL_CHECKS.md)).
3. M18.
