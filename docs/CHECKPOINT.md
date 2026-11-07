# 체크포인트: 어디까지 했고, 어떻게 이어가는지

마지막 갱신: 2026-11-07(로컬 macOS에서 백엔드 재확인, Android 빌드 직전까지 준비). 남은 작업은 **로컬에서** 이어간다. 이 파일만 읽으면 바로 시작할 수 있게 쓴다.
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
| #13 (초안) | `claude/m12-android-parent` | M12 준비: 백엔드 보강, API 계약, Android 골격 | 이 체크포인트 |
| — | `wip/m12-android-partial` | M12 앱 코드 일부(빌드·리뷰 안 됨). **병합 금지, 참고용** | 보관 |

`claude/m12-android-parent`에 들어간 것:
- 백엔드: `GET /v1/me`, `GET /v1/families/{id}/cases`, 로그인 nonce(`POST /v1/auth/nonce`, Apple/Google 로그인에 nonce 필수). `signin_nonces` 테이블 추가.
- `docs/API_CONTRACT.md`: 코드에서 옮기고 경로별로 코드·실행 중인 백엔드와 대조해 고친 클라이언트 계약.
- `android/`: Gradle 9.4.1 / AGP 9.2.1 / Kotlin 2.2.10 / Compose BOM 2025.06.01 골격(Fitrip 앱과 같은 툴체인). 화면은 자리표시 하나뿐.
- #12의 보안 수정(운영에서 FastAPI 문서 경로 끄기)까지 병합해 둠.
- 테스트: 백엔드 전체 **682 passed, 1 skipped**(건너뛴 1개는 안내 음성 mp3가 아직 없어서). Android 골격 빌드는 이 환경에서 **끝까지 확인하지 못했다**(첫 빌드가 의존성 다운로드 중 시간 제한에 걸린 뒤 중단).

### 2026-11-06 로컬(macOS) 확인 결과
- 코드 변경 없음. 이 커밋은 문서만 고친다.
- 백엔드: `PGTZ=UTC`로 돌리면 **682 passed, 1 skipped**(클라우드와 같음). `PGTZ` 없이 Postgres 서버 시간대가 UTC가 아니면 `tests/test_me.py` 2개가 실패한다(아래 4절 "코드에서 발견한 것").
- 개발 서버(DEV_AUTH)를 띄워 `/docs` 200, `POST /v1/auth/nonce` 201 확인.
- Android: `local.properties`(SDK 경로)만 만들고 **Gradle은 아직 한 번도 실행하지 않았다.** 다음 작업이 첫 빌드다(5.3).

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

### PR #5~#12 리뷰와 병합
- 병합 전 전체 리뷰를 워크플로(리뷰어 10 + 지적마다 반박 검증 3)로 돌리다가 **토큰 사용이 커서 중단**했다. 수정이나 커밋은 하나도 나가지 않았다.
- 병합은 아직 안 했다. #5부터 순서대로 병합하고, 병합할 때마다 다음 PR의 base를 `main`으로 바꾼다(브랜치를 지우면 GitHub가 자동으로 바꾼다).
- 리뷰가 필요하면 PR 단위로 가볍게(`/code-review low` 등) 하는 것을 권한다.

### 코드에서 발견한 것
- ~~운영에서 FastAPI 기본 문서 경로가 열려 있다~~ → **고침** (#12, `Stop serving the generated API docs outside DEV_AUTH`).
- [API_CONTRACT.md §11](API_CONTRACT.md)의 목록: 활성 자녀 제거·가족 탈퇴·로그아웃·가족 이벤트 조회 경로 없음, 만료 시각이 지나도 `invite_expires_at`/`allow_link_open`이 남음, 앱 없는 자녀에게 앱 초대를 다시 발급할 수 있음, `502 sms_failed`가 커밋 뒤에 나감, `code_check_slow`를 내보내는 곳 없음.
- **API 시각이 DB 세션 시간대를 따른다.** `_iso()`(`backend/api.py`)가 Postgres가 돌려준 `timestamptz`를 그대로 `isoformat()`해서, 서버 시간대가 `America/Chicago`면 `-06:00`으로 나간다. 시각 자체는 맞지만 계약 예시(`+00:00`)와 테스트는 UTC를 가정한다. 고치지 않았다. 연결 시 세션을 UTC로 고정(`options="-c TimeZone=UTC"`)하거나 `_iso()`에서 UTC로 바꾸는 방안 중 결정 필요. 그 전까지는 `PGTZ=UTC`를 붙여 테스트·서버를 돌린다.

### 정해 둔 기본값 (바꾸려면 말하면 됨)
- Android 패키지명 `com.familyshield.app`(`-PfsApplicationId`로 변경 가능).
- 자녀당 케이스 상한은 **부모 1명 기준** 하루 5건, 부모당 10건.
- 앱 없는 자녀 링크 유효기간 72시간, 초대 코드 24시간.
- Claude 분석 기본 모델 `claude-sonnet-5-5`(`CLAUDE_MODEL`), 서버 측 거절 폴백 켬.

## 5. 로컬에서 이어가기

### 5.1 코드 받기
```bash
git clone https://github.com/byungwoook/family-shield.git && cd family-shield
git checkout claude/m12-android-parent   # 스택 맨 위. #5~#12 변경과 M12 준비가 모두 들어 있다
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
- **골격 빌드를 아직 한 번도 끝까지 확인하지 못했다.** 첫 작업은 위 빌드 명령이다.

### 5.4 M12 작업 순서
1. 계약은 [API_CONTRACT.md](API_CONTRACT.md)가 기준이다(코드와 대조해 검증됨).
2. `wip/m12-android-partial`의 코드(약 2,000줄)는 한 번도 컴파일되지 않았다. 참고만 하고, 쓸 부분은 검토해서 가져온다:
   - API 클라이언트, Keystore 세션 암호화, 저장소
   - 결과 문구 매핑, 로그인·가족 만들기 화면, en/ko 문자열
3. 완료 기준(설계 문서 M12):
   - 화면: Google 로그인, 가족 만들기, 초대 코드 표시, 자녀 확인, 자녀를 골라 메시지를 붙여 케이스 열기, `GET /v1/cases/{id}` 폴링, 초록/빨강/노랑 문구(en, ko).
   - UI 테스트: 빈 가족, 확인 전 자녀(Verify 비활성), 노랑 결과, 빨강 결과. 로컬에서는 에뮬레이터 UI 테스트로 확인할 수 있다.
4. [resume/m12-android-workflow.js](resume/m12-android-workflow.js)는 이번에 쓴 다중 에이전트 계획이다. 토큰을 많이 쓰니 **필요할 때만** 참고한다. 경로는 클라우드 컨테이너 기준이다.

### 5.5 그다음
1. M13 공유 인텐트 → M14 Android 자녀 화면.
2. iOS M9–M11: Mac에서 Xcode로. `docs/API_CONTRACT.md`와 같은 계약을 쓴다.
3. M17.
4. 키가 필요한 수동 확인([MANUAL_CHECKS.md](MANUAL_CHECKS.md)).
5. M18.
