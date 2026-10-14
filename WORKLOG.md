# GameModeBridge 작업 기록

CLAUDE.md는 개발 지침이고, 이 문서는 실제로 진행한 작업과 결정 사항을 시간순으로 기록함.

---

## 진행 현황 (2026-10-14 기준)

| 단계 | 상태 | 커밋 |
|---|---|---|
| 0단계: 환경 구성 | 완료 | `64b2020` |
| 1단계: 루틴 감지 검증 | 생략 (사용자 결정) | `419f101` |
| 2단계: 암호화 모듈 | 완료 | `e76053c` |
| 3단계: 안드로이드 수신 처리 | 시작 전 | |
| 4단계 이후 | 시작 전 | |

---

## 2026-10-13 ~ 2026-10-14 작업 내용

### □ 개발 도구 설치
- Microsoft OpenJDK 17 (17.0.20.101): winget 공식 패키지로 설치
  - ◦ 경로: `C:\Program Files\Microsoft\jdk-17.0.20.101-hotspot`
  - ◦ 사용자 환경 변수 `JAVA_HOME`에 등록함
- Android Studio 2026.2.1.8: winget 공식 패키지로 설치 (아직 실행하지 않음)
- Android SDK: `%LOCALAPPDATA%\Android\Sdk`
  - ◦ 명령줄 도구는 Google 공식 저장소에서 내려받아 SHA-1 체크섬 확인 후 설치함
  - ◦ platform-tools 설치, 라이선스 동의 완료
  - ◦ 플랫폼과 빌드 도구는 첫 빌드 때 Android Gradle 플러그인이 자동으로 내려받음
- Gradle 9.8.1: SHA-256 체크섬 확인 후 임시 폴더에서 Gradle Wrapper 생성에만 사용함 (전역 설치 안 함)
- Python 3.12.5: 기존 설치본 사용

### □ 0단계: 환경 구성
- PC
  - ◦ `pc/.venv` 전용 가상환경 생성 (Python 3.12.5)
  - ◦ `requirements.txt`, `requirements-dev.txt`에 버전 고정 (pywin32는 Windows에서만 설치)
  - ◦ 빈 테스트 통과 확인
- 안드로이드
  - ◦ 패키지 `com.gamemodebridge`, minSdk 26, compileSdk 36, targetSdk 36
  - ◦ AGP 9.4.1 (내장 Kotlin 2.2.10), Gradle Wrapper 9.8.1 (배포 파일 체크섬 고정)
  - ◦ `gradle/libs.versions.toml`로 버전 관리
  - ◦ `allowBackup=false`, 릴리스 빌드 R8 난독화 및 코드 축소 설정
  - ◦ 빈 JVM 테스트 통과 확인
- `.gitignore`: 가상환경, 비밀 정보 파일(config.json, 서비스 계정 JSON, sa.bin, google-services.json), 빌드 산출물 제외

### □ 프로젝트 위치 이동
- 처음 위치 `E:\개인앱개발\GameModeBridge`에서 `E:\dev\GameModeBridge`로 이동함
- 이유: Android Gradle 플러그인이 Windows에서 한글 경로 빌드를 거부함
- 원본 지침 파일(`CLAUDE (1).md`)과 `개선사항.txt`는 `E:\개인앱개발`에 그대로 있음

### □ CLAUDE.md 개선사항 반영
- `개선사항.txt`의 검토 의견을 반영함
  - ◦ 메시지 순번(seq) 도입: FCM 순서 역전과 재전송 방지. 기존 최근 msg_id 50개 검사를 대체함
  - ◦ 메시지 의미 변경: `event: start/stop`에서 현재 원하는 상태 `state: on/off`로 변경
  - ◦ 상태 동기화 규칙: PC 앱 시작, 발송 실패 후 복구, 절전 해제, 사용자 요청 시 현재 상태 발송
  - ◦ FCM 옵션: priority HIGH, ttl 60s, collapse_key `gmb_state`, 접근 토큰 재사용
  - ◦ 10초 목표를 보장값이 아닌 실기기 검증 목표로 재정의
  - ◦ 확인 가능한 상태 표시: FCM 접수를 모드 전환 완료로 표시하지 않음
  - ◦ 재등록 절차: 일반 재등록(확인 후 교체)과 유출 대응 재등록(즉시 교체) 구분, QR 형식 검증 규칙
  - ◦ 감지 경계 규칙: 종료 유예 4초, 조회 실패 시 상태 유지, 중복 실행 방지, `list-proc` 명령
  - ◦ 루틴 설정 주의: 종료 시 원래대로 돌리기 옵션 해제, 전용 사용자 지정 모드 권장
  - ◦ 디버그 시뮬레이터는 별도 테스트 키 사용, 평문 키 취급 범위 정리
  - ◦ 작업 규칙: 문서에 정한 의존성은 확인 없이 설치, 단계 완료마다 커밋, 테스트 결과 보고 형식

### □ 1단계 생략
- 사용자 결정으로 루틴 감지 실기기 검증을 진행하지 않음
- 기본값으로 진행: 알림 채널 중요도 기본, 알림 삭제 5초 후
- 수동 게임 모드 끄기 버튼은 3단계에서 만듦
- 확인하지 않은 항목은 CLAUDE.md 13장에 기록함

### □ GitHub 연동
- 비공개 저장소: https://github.com/TIRIAS/GameModeBridge (원격 이름 `origin`, 브랜치 `main`)
- 저장되어 있던 잘못된 GitHub 로그인 정보를 지우고 Git Credential Manager로 다시 로그인함
- 단계 커밋 후 push하는 규칙을 CLAUDE.md 10장에 추가함

### □ 2단계: 암호화 모듈
- PC `pc/gmb/crypto.py`
  - ◦ AES-256-GCM 봉투 `{v, iv, ct}` 생성 (`seal`) 및 복호화 (`open_envelope`)
  - ◦ IV는 메시지마다 `secrets.token_bytes(12)`로 생성, AAD `GMB-v1`, base64url(패딩 없음)
  - ◦ 고정 IV를 받는 `seal_with_iv`는 테스트 벡터 생성에만 사용함
- 테스트 벡터 `pc/tools/make_testvectors.py` → `shared/testvectors/crypto_v1.json`
  - ◦ 정상 3종: 영문 게임 이름, 한글 게임 이름, 빈 게임 이름
  - ◦ 위변조 6종: 암호문 변조, IV 변조, 다른 키, 다른 AAD, 태그 잘림, 버전 불일치
  - ◦ 고정 키는 테스트 전용 값(0x00부터 0x1F)이며 비밀 정보가 아님
- 안드로이드 `CryptoManager.kt`
  - ◦ `CryptoManager` 인터페이스와 `AesGcmCryptoManager` 구현 (키는 주입받음)
  - ◦ 실패 사유 코드 `VERSION`, `FORMAT`, `AUTH` (3단계 폐기 로그에 사용)
- 안드로이드 JVM 테스트가 같은 테스트 벡터 파일로 교차 검증함
  - ◦ JSON 처리는 사용자 선택에 따라 kotlinx.serialization 1.9.0 사용 (현재 테스트 전용)
- 테스트 결과
  - ◦ PC: `pytest` 25 passed
  - ◦ 안드로이드: `gradlew.bat testDebugUnitTest` CryptoManagerTest 4개, SmokeTest 1개 통과

---

## 주요 결정 사항

| 항목 | 결정 | 이유 |
|---|---|---|
| Python 버전 | 3.12.x | 개발 PC에 설치된 버전, 3.11 이상 조건 충족 |
| 프로젝트 위치 | `E:\dev\GameModeBridge` | 한글 경로에서 안드로이드 빌드 불가 |
| 패키지 이름 | `com.gamemodebridge` | Claude Code 경로 혼선 방지를 위해 고정 |
| compileSdk, targetSdk | 36 | 현재 안정 버전, 알림 권한 처리 포함 |
| 1단계 | 생략 | 사용자 결정 |
| 알림 채널 중요도 | 기본 | 루틴 감지 미검증이므로 감지 가능성이 높은 쪽 |
| 감지 일시정지 정책 | 게임 중이면 off 1회 발송, 해제 시 현재 상태 발송 | 휴대폰이 게임 모드에 남는 상황 방지 |
| 사용자가 모드를 직접 끈 경우 | 다시 켜지 않음 | 동기화 상황 외에는 on을 다시 보내지 않음 |
| 안드로이드 JSON 처리 | kotlinx.serialization | 사용자 선택. JVM 테스트에서 내장 org.json 사용 불가 |
| GitHub 저장소 | 비공개 | 저장소를 통한 비밀 정보 노출 위험 감소 |

---

## 다음 작업

### □ 3단계: 안드로이드 수신 처리
- Firebase 없이 먼저 진행 가능한 부분
  - ◦ `MessageProcessor` (5장 수신 처리 순서), `SeqStore` (순번 저장)
  - ◦ 디버그 시뮬레이터 화면, 수동 게임 모드 끄기 버튼, 상태 표시, 알림 권한 요청
  - ◦ kotlinx.serialization을 앱 의존성으로 옮기고 직렬화 플러그인(Kotlin 2.2.10에 맞춤) 추가
- 사용자가 해야 할 일 (Firebase 연결 전 필요)
  - ◦ Firebase 콘솔에서 프로젝트 생성
  - ◦ 안드로이드 앱 등록 (패키지 이름 `com.gamemodebridge`)
  - ◦ `google-services.json`을 `android/app/`에 넣기 (커밋되지 않음)

### □ 참고
- 새 터미널에서 `gradlew.bat`가 JDK를 못 찾으면 `JAVA_HOME` 설정 전에 열린 창이므로 새로 열면 됨
- 작업 중 요청된 `conda activate base`는 CLAUDE.md 2장 규칙(conda base 사용 금지)에 따라 실행하지 않음
