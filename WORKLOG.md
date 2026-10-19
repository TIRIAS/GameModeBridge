# GameModeBridge 작업 기록

CLAUDE.md는 개발 지침이고, 이 문서는 실제로 진행한 작업과 결정 사항을 시간순으로 기록함.

---

## 진행 현황 (2026-10-14 기준)

| 단계 | 상태 | 커밋 |
|---|---|---|
| 0단계: 환경 구성 | 완료 | `64b2020` |
| 1단계: 루틴 감지 검증 | 생략 (사용자 결정) | `419f101` |
| 2단계: 암호화 모듈 | 완료 | `e76053c` |
| 3단계: 안드로이드 수신 처리 | 완료 (실제 FCM 수신은 4, 5단계에서 확인) | `656e871` 외 |
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

## 2026-10-19 작업 내용

### □ 테스트 기기 연결 (안드로이드 태블릿)
- 기기: Lenovo Legion Y700 (TB322FC), Android 15 (API 35), ZUXOS 1.1.10 중국 내수용 ROM
- Google Play 서비스와 Play 스토어 있음 (FCM 수신 가능)
- 갤럭시가 아니므로 삼성 모드 및 루틴 동작은 확인할 수 없음. 메시지 검증과 알림 게시까지 확인 가능함
- 중국 내수용 ROM은 백그라운드 제한이 강할 수 있으므로 FCM 수신 시험 시 배터리 최적화 예외, 자동 실행 허용 확인 필요
- Wi-Fi를 쓸 수 없어 USB 디버깅으로 연결함

### □ USB 디버깅 인식 문제 해결
- 증상: Windows가 태블릿 ADB 인터페이스에 일반 WinUSB 드라이버를 붙였으나 `adb devices`에 기기가 나오지 않음
- 원인: 장치에 adb 인터페이스 GUID가 등록되지 않아 adb가 장치를 찾지 못함
- 조치: 관리자 권한으로 해당 장치 하나의 레지스트리에 값을 추가하고 장치를 재시작함 (드라이버 설치 없음)
  - ◦ 위치: `HKLM\SYSTEM\CurrentControlSet\Enum\USB\VID_17EF&PID_7F41&MI_01\6&2A38517D&0&0001\Device Parameters`
  - ◦ 값: `DeviceInterfaceGUIDs` (REG_MULTI_SZ) = `{F72FE0D4-CBCB-407d-8814-9ED673D0DD6B}`
  - ◦ 되돌리기: 위 값만 삭제하면 됨
  - ◦ 다른 USB 포트에 꽂으면 장치 경로가 달라져 같은 조치가 다시 필요할 수 있음
- 결과: `adb devices`에 `HA2ABNWM` 인식, USB 디버깅 허용 후 `gradlew.bat installDebug`로 설치 및 실행 확인

### □ 3단계 중 Firebase 제외 부분
- `MessageProcessor.kt`: 5장 수신 처리 순서 1~7 구현, 폐기 사유 코드 `VERSION`, `FORMAT`, `AUTH`, `STATE`, `STALE`, `FUTURE`, `SEQ`
  - ◦ 평문은 kotlinx.serialization의 JsonElement로 직접 읽음 (직렬화 컴파일러 플러그인 불필요). 라이브러리를 앱 의존성으로 옮김
  - ◦ 게임 이름 정리: 제어 문자와 서식 문자 제거, 키워드는 대소문자 무시하고 변화가 없을 때까지 반복 제거, 코드 포인트 기준 50자
- `SeqStore.kt`: 마지막 처리 순번을 SharedPreferences에 동기 저장 (알림 게시 전 저장)
- `NotificationHelper.kt`: 루틴 키워드 상수, 채널 중요도 기본, 잠금 화면 비공개, `setTimeoutAfter`로 5초 후 자동 삭제
  - ◦ minSdk 26이므로 androidx NotificationCompat 대신 기본 `Notification.Builder` 사용 (의존성 추가 없음)
- `StatusStore.kt`, `MainActivity.kt`: 알림 권한 상태, 마지막 처리 결과(앱이 확인 가능한 범위만), 수동 게임 모드 끄기, 알림 권한 요청, 배터리 최적화 설정 열기
- debug 전용: `SimulatorActivity.kt`, `EnvelopeFactory.kt` (실행마다 새로 만드는 테스트 키, 별도 순번 저장소 `gmb_sim_seq`)
- 테스트
  - ◦ `gradlew.bat testDebugUnitTest`: 28개 통과 (MessageProcessorTest 23, CryptoManagerTest 4, SmokeTest 1)
  - ◦ MessageProcessorTest는 debug 전용 EnvelopeFactory를 쓰므로 `src/testDebug`에 둠
  - ◦ `gradlew.bat assembleRelease` 성공. 릴리스 APK에 SimulatorActivity와 EnvelopeFactory 없음, 권한은 POST_NOTIFICATIONS 하나뿐임을 apkanalyzer로 확인
- 태블릿 실기기 확인 (사용자 확인)
  - ◦ 정상 켜기와 끄기: 알림이 뜨고 5초 후 사라짐
  - ◦ 오래된 메시지 STALE, 재전송 SEQ, 순서 역전 시 늦게 온 켜기 SEQ, 위변조 AUTH로 폐기됨
  - ◦ 처음 만든 재전송 버튼은 직전 메시지(오래된 메시지)를 다시 보내 STALE로 걸렸음. 마지막 정상 메시지를 다시 보내도록 수정 후 SEQ 확인
- 남은 일: Firebase 연결, 토픽 구독, `GameModeMessagingService` (사용자의 `google-services.json` 필요)

### □ 3단계 Firebase 연결
- 사용자가 Firebase 프로젝트 `gamemodebridge` 생성 및 안드로이드 앱 `com.gamemodebridge` 등록
  - ◦ 콘솔 화면이 안내와 달라 캡처를 보고 진행함. 프로젝트 이름 아래 **+ 앱 추가** 버튼에서 등록함
- `google-services.json`을 `android/app/`에 둠 (.gitignore로 커밋 제외 확인, 파일 내용은 패키지 이름만 확인)
- Firebase BoM 35.0.2, firebase-messaging, google-services 플러그인 4.5.0 추가
- `GameModeMessagingService.kt`: 데이터 메시지를 `MessageProcessor`로 처리하고 결과를 `StatusStore`에 기록. 폐기 시 사유 코드만 로그에 남김
  - ◦ 서비스는 `exported=false`
  - ◦ 등록 토큰은 다루지 않음 (토픽 방식)
- `KeyStoreManager.kt`: Keystore의 공유 키 조회만 구현. 키가 없으면 `NOT_REGISTERED`로 폐기 (키 가져오기는 4단계)
- 권한: FCM 라이브러리가 자동 추가하는 일반 권한을 CLAUDE.md 11장에 예외로 기록함
- 확인 결과
  - ◦ JVM 테스트 28개 통과, 릴리스 빌드 성공
  - ◦ 태블릿 logcat에서 `FirebaseApp initialization successful` 확인
  - ◦ 실제 FCM 메시지 수신은 키와 토픽이 생기는 4단계, PC 발송이 생기는 5단계에서 확인함

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

### □ 4단계: 기기 등록
- PC `register` 명령 (키와 토픽 생성, QR 표시, 완료 확인 후 keyring 저장), `register --revoke`
- 안드로이드 `RegistrationActivity` (QR 스캔과 형식 검증, Keystore 가져오기, 토픽 구독, 첫 정상 메시지 수신 시 확정)
- Google 코드 스캐너(ML Kit) 의존성 추가 필요 (3장에 정한 의존성)
- 태블릿은 중국 내수용 ROM이므로 백그라운드 수신 시 배터리 최적화 예외, 자동 실행 허용 확인

### □ 참고
- 새 터미널에서 `gradlew.bat`가 JDK를 못 찾으면 `JAVA_HOME` 설정 전에 열린 창이므로 새로 열면 됨
- 작업 중 요청된 `conda activate base`는 CLAUDE.md 2장 규칙(conda base 사용 금지)에 따라 실행하지 않음
