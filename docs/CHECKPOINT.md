# 체크포인트: 어디까지 했고, 어떻게 이어가는지

마지막 갱신: 2026-11-05. 이 파일만 읽으면 다음 세션이 바로 이어갈 수 있게 쓴다.
설계의 권위는 [PRODUCT_REDESIGN.md](PRODUCT_REDESIGN.md), API의 권위는 코드와 그것을 옮긴 [API_CONTRACT.md](API_CONTRACT.md)다.

## 1. 한 줄 요약

백엔드는 v1 범위(M1–M8, M15, M16)가 끝났다. 모바일 앱은 Android 프로젝트 골격과 앱이 쓸 API 계약까지만 있고, **앱 구현(M12)은 시작 전 상태로 멈췄다.**

## 2. PR 스택 (포크 `byungwoook/family-shield`, 원본에는 PR 없음)

각 PR은 앞 PR 위에 쌓여 있다. 앞에서부터 병합하면 GitHub가 다음 PR의 base를 `main`으로 바꾼다.

| PR | 브랜치 | 내용 | 상태 |
|---|---|---|---|
| #5 | `cursor/api-without-handset-da64` | M4 휴대폰 없이 테스트하는 API | 열림 |
| #6 | `claude/m5-signin-invites-otp` | M5 Apple/Google 로그인, 초대, SMS OTP, 부모 확인 | 열림 |
| #7 | `claude/m6-twilio-keypad-call` | M6 Twilio 키패드 대체 전화 | 열림 |
| #8 | `claude/followups-child-view-timeline-otp-voice` | 자녀 화면 축소, 타임라인 순서, OTP 음성 대체 | 열림 |
| #9 | `claude/m7-voice-note-claims` | M7 음성 메모 → 주장·사기 유형 | 열림 |
| #10 | `claude/m8-push` | M8 푸시(APNs/FCM)와 케이스 타이머 | 열림 |
| #11 | `claude/m15-number-change-caps` | M15 번호 변경, 케이스 상한, 24시간 규칙 | 열림 |
| #12 | `claude/m16-call-only-child` | M16 앱 없는 자녀(SMS 링크 페이지) | 열림 |
| (초안) | `claude/m12-android-parent` | M12 준비: 백엔드 보강, API 계약, Android 골격 | 이 체크포인트 |
| — | `wip/m12-android-partial` | M12 앱 코드 일부(빌드·리뷰 안 됨). **병합 금지, 참고용** | 보관 |

`claude/m12-android-parent`에 들어간 것:
- 백엔드: `GET /v1/me`, `GET /v1/families/{id}/cases`, 로그인 nonce(`POST /v1/auth/nonce`, Apple/Google 로그인에 nonce 필수). `signin_nonces` 테이블 추가.
- `docs/API_CONTRACT.md`: 코드에서 옮기고 경로별로 코드·실행 중인 백엔드와 대조해 고친 클라이언트 계약.
- `android/`: Gradle 9.4.1 / AGP 9.2.1 / Kotlin 2.2.10 / Compose BOM 2025.06.01 골격(Fitrip 앱과 같은 툴체인). 화면은 자리표시 하나뿐.
- 테스트: 백엔드 전체 **681 passed, 1 skipped**(건너뛴 1개는 안내 음성 mp3가 아직 없어서). Android 골격 빌드는 이 환경에서 **끝까지 확인하지 못했다**(첫 빌드가 의존성 다운로드 중 시간 제한에 걸린 뒤 중단).

## 3. 마일스톤 현황

| 마일스톤 | 상태 |
|---|---|
| M1–M8, M15, M16 (백엔드) | 완료, PR #2–#12 |
| M12 Android 부모 화면 | **준비만 완료.** 백엔드 보강·계약·골격 있음. 앱 구현 전 |
| M13 Android 공유 인텐트, M14 Android 자녀 화면 | 시작 전 |
| M9–M11 iOS | 시작 전. 이 Linux 환경엔 Swift/Xcode가 없어 빌드 검증 불가(Mac 필요) |
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

### 코드에서 발견한 것 (아직 안 고침)
- **운영에서 FastAPI 기본 문서 경로가 열려 있다**: `GET /docs`, `/redoc`, `/openapi.json`이 200으로 응답한다. `boot()`에서 `DEV_AUTH`가 아니면 `FastAPI(docs_url=None, redoc_url=None, openapi_url=None)`로 끄는 것이 맞다. 작은 수정, 테스트 하나 추가.
- [API_CONTRACT.md §11](API_CONTRACT.md)의 목록: 활성 자녀 제거·가족 탈퇴·로그아웃·가족 이벤트 조회 경로 없음, 만료 시각이 지나도 `invite_expires_at`/`allow_link_open`이 남음, 앱 없는 자녀에게 앱 초대를 다시 발급할 수 있음, `502 sms_failed`가 커밋 뒤에 나감, `code_check_slow`를 내보내는 곳 없음.

### 정해 둔 기본값 (바꾸려면 말하면 됨)
- Android 패키지명 `com.familyshield.app`(`-PfsApplicationId`로 변경 가능).
- 자녀당 케이스 상한은 **부모 1명 기준** 하루 5건, 부모당 10건.
- 앱 없는 자녀 링크 유효기간 72시간, 초대 코드 24시간.
- Claude 분석 기본 모델 `claude-sonnet-5-5`(`CLAUDE_MODEL`), 서버 측 거절 폴백 켬.

## 5. 이어가기: M12 Android 부모 화면

### 5.1 환경 다시 만들기 (새 클라우드 컨테이너 기준)
```bash
# Python 백엔드
python3 -m venv /tmp/fsvenv && /tmp/fsvenv/bin/pip install -r requirements.txt
# 로컬 Postgres: docker compose up -d (또는 로컬 postgres를 띄우고 DATABASE_URL 지정)
DATABASE_URL=postgresql://familyshield:familyshield@127.0.0.1:5432/familyshield /tmp/fsvenv/bin/python -m pytest -q

# Android SDK (KVM이 없어 에뮬레이터는 못 씀; JVM 테스트만)
mkdir -p /opt/android-sdk/cmdline-tools && cd /opt/android-sdk/cmdline-tools
curl -sSO https://dl.google.com/android/repository/commandlinetools-linux-14742923_latest.zip
unzip -q commandlinetools-linux-14742923_latest.zip && mv cmdline-tools latest
yes | latest/bin/sdkmanager --sdk_root=/opt/android-sdk --licenses
latest/bin/sdkmanager --sdk_root=/opt/android-sdk "platform-tools" "platforms;android-36" "build-tools;36.0.0"
```

Gradle을 돌릴 때 지켜야 할 것(이 환경에서 겪은 문제):
- `export ANDROID_HOME=/opt/android-sdk LANG=C.UTF-8 LC_ALL=C.UTF-8`: 한글 테스트 이름 때문에 UTF-8 로캘이 없으면 Kotlin 컴파일러가 죽는다.
- `./gradlew --no-daemon --max-workers=2 -Dorg.gradle.internal.repository.max.tentatives=12 -Dorg.gradle.internal.repository.initial.backoff=3000 ...`: 프록시를 통한 Maven Central이 429를 주므로 동시 다운로드를 줄이고 재시도한다.
- 첫 빌드는 의존성 다운로드로 25분 넘게 걸릴 수 있다. 시간 제한 없이 백그라운드로 돌린다. Gradle 빌드는 한 번에 하나만.

로컬 백엔드(Android e2e 테스트용, DEV_AUTH):
```bash
ENV=development DEV_AUTH=1 TIMER_SECONDS=1 DATABASE_URL=postgresql://.../familyshield_e2e \
CODE_PEPPER=e2e-pepper-0123456789 OTP_DERIVATION_KEY=e2e-derivation-0123456789 \
uvicorn --factory backend.api:boot --host 127.0.0.1 --port 8000
```
`familyshield_e2e`는 빈 DB에 `backend.store.apply_schema`를 적용해 만든다.

### 5.2 작업 순서
1. `claude/m12-android-parent`를 체크아웃하고 **골격 빌드부터** 확인한다: `./gradlew ... assembleDebug testDebugUnitTest`.
2. 구현은 [resume/m12-android-workflow.js](resume/m12-android-workflow.js)의 계획을 따른다. 이 스크립트는 이번 세션에서 실제로 쓴 워크플로다(경로는 이번 컨테이너 기준이라 맞게 고친다). Backend·Contract 단계는 **이미 끝났으니 건너뛰고** Implement부터: 구현 → 4개 관점 병렬 리뷰(API 계약, 안전·문구 규칙, UX·한국어, 테스트) → 지적마다 반박 검증 → 수정 → 누락 점검 루프.
3. `wip/m12-android-partial`의 코드(약 2,000줄: API 클라이언트, Keystore 세션 암호화, 저장소, 결과 문구 매핑, 로그인·가족 만들기 화면, en/ko 문자열)는 한 번도 컴파일되지 않았다. 참고만 하고, 쓸 부분은 검토해서 가져온다.
4. M12 완료 기준(설계 문서): Google 로그인, 가족 만들기, 초대 코드 표시, 자녀 확인, 자녀 고르고 메시지 붙여 케이스 열기, `GET /v1/cases/{id}` 폴링, 초록/빨강/노랑 문구(en, ko). UI 테스트: 빈 가족, 확인 전 자녀(Verify 비활성), 노랑 결과, 빨강 결과. 에뮬레이터 대신 Robolectric UI 테스트와 로컬 백엔드 상대 JVM e2e 테스트로 확인한다.

### 5.3 그다음
M13(공유 인텐트) → M14(Android 자녀 화면) → iOS M9–M11(Mac에서 빌드 확인 필요) → M17 → 키가 필요한 수동 확인 → M18.
