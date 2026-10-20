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
| 4단계: 기기 등록 | 완료 (새 키 확정도 5단계에서 확인됨) | `2011cf4` |
| 5단계: PC 발송 모듈 | 완료 | `8de2351` |
| 6단계: PC 게임 감지 | 완료 | `1d950b5` |
| 7단계: 트레이 앱 통합 | 진행 중 (재부팅 자동 실행 확인 남음, 보안 점검 9번 확인 불가) | `1a87b1b` 외 |
| 8단계 | 시작 전 (게임 목록 편집 UI는 7단계에서 구현) | |

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

### □ 4단계: 기기 등록
- PC
  - ◦ `secret_store.py`: keyring(Windows 자격 증명 관리자)에 공유 키와 토픽 저장. `Credentials` 출력 시 키를 숨김
  - ◦ `state_store.py`: 순번 보존 (`%APPDATA%/GameModeBridge/state.json`). 재등록 시 순번 초기화가 필요해 5단계에서 4단계로 당겨 구현함
  - ◦ `registration.py`: 키와 토픽 생성, QR 문자열 `GMB1:<토픽>:<키>`, 등록 절차(완료 시 확정, 취소 시 기존 유지, `--revoke` 시 즉시 삭제), tkinter QR 창
  - ◦ QR 창은 60초 후 창을 닫는 대신 QR과 문자열만 숨기도록 변경함 (창을 닫으면 완료 버튼도 사라지므로). CLAUDE.md 6장에 반영
  - ◦ `__main__.py`: `python -m gmb register [--revoke]`
- 안드로이드
  - ◦ `KeyStoreManager.kt`: `KeyVault` 인터페이스와 Keystore 구현. 키는 복호화 전용(PURPOSE_DECRYPT, GCM)으로 가져옴
  - ◦ `DeviceRegistration.kt`: QR 형식 검증(`QrPayload`), 키 슬롯 2개(`gmb_key_a`, `gmb_key_b`)로 active와 pending 관리
    - 새 등록은 pending 슬롯에 키를 넣고 새 토픽 구독. 구독 실패 시 pending만 지우고 기존 연결 유지
    - 메시지가 온 토픽(`/topics/...`)으로 사용할 키를 고름. pending 토픽에서 온 첫 정상 메시지의 순번을 저장하는 시점에 교체 확정 (이전 토픽 구독 해제, 이전 키 삭제, 순번 새로 시작)
    - 긴급 재등록: 키, 토픽, 순번 모두 즉시 삭제
    - 폐기 사유 추가: `NOT_REGISTERED`, `TOPIC`
  - ◦ `RegistrationActivity.kt`: Google 코드 스캐너(16.1.0, 카메라 권한 불필요), 문자열 직접 입력(자동 완성과 추천 끔), 긴급 재등록 확인 창. 토픽은 앞 8자만 표시
  - ◦ 메인 화면에 기기 등록 버튼과 등록 상태 표시
- 보안 확인
  - ◦ 릴리스 APK 권한 목록에 카메라 등 추가 권한 없음
  - ◦ 외부 공개 구성 요소는 MainActivity와 FCM 수신기(c2dm SEND 권한으로 보호)뿐. CLAUDE.md 11장에 FCM 수신기 예외 기록
- 테스트
  - ◦ PC `pytest`: 36 passed
  - ◦ 안드로이드 `testDebugUnitTest`: 41개 통과 (DeviceRegistrationTest 10, QrPayloadTest 3 추가)
- 실기기 확인
  - ◦ PC `register` 실행, 태블릿에서 QR 스캔, 새 토픽 구독 성공, PC에서 완료 누름
  - ◦ PC keyring에 키와 토픽 저장됨, 태블릿은 확정 대기(pending) 상태
  - ◦ PC와 태블릿 토픽 일치 확인 (값을 출력하지 않고 비교)
  - ◦ 키 일치와 확정은 5단계에서 PC가 새 키로 첫 메시지를 보낼 때 확인함

### □ 5단계: PC 발송 모듈
- 사용자가 Google Cloud 콘솔에서 전용 서비스 계정 `gmb-sender` 생성 (역할: Firebase Cloud Messaging API 관리자), JSON 키 발급
  - ◦ 키 파일은 `client_email`, `type`, `project_id`만 읽어 확인하고 비밀 키는 열람하지 않음
  - ◦ 기존 `firebase-adminsdk` 계정은 권한이 넓어 사용하지 않음
- `import-sa` 명령: 서비스 계정 JSON 형식 검증 후 DPAPI로 암호화하여 `%APPDATA%/GameModeBridge/sa.bin` 저장. 원본 삭제는 사용자에게 안내 (자동 삭제 안 함)
- `sender.py`: FCM HTTP v1, priority HIGH, ttl 60s, AuthorizedSession으로 접근 토큰 재사용, 같은 봉투로 최대 3회 재시도(1, 2, 2초 간격), 400/401/403/404는 재시도 안 함, 드라이런과 메모리 발송자
- `crypto.make_payload`: 평문 생성 (msg_id 매번 새로 생성)
- `tools/simulate.py`: basic, stale, replay, reorder, tamper (multi, flapping은 6단계)
- 안드로이드: 처리 결과(사유 코드만)를 모두 로그에 남기도록 변경 (지연 측정용)
- 테스트: PC `pytest` 60 passed (sender, simulate, secret_store 추가)
- 실기기 확인 (사용자 승인 후 실제 발송)
  - ◦ `simulate basic --live`: 켜기와 끄기 모두 수신. 태블릿 pending 등록이 active로 확정되어 키 일치 확인. 순번 PC 4, 태블릿 4 일치
  - ◦ stale STALE, replay SEQ, reorder SEQ, tamper AUTH로 모두 폐기됨
- 발견한 문제와 조치
  - ◦ PC 시계가 실제 시각보다 약 22초 느림 (태블릿은 자동 시간으로 정확). 허용 범위 안이라 동작에는 문제없음. 사용자는 보정 기능을 제안했으나 보정값이 틀어질 위험 때문에 넣지 않고 PC 시간 동기화를 권장함 (사용자는 일단 진행 결정)
  - ◦ collapse_key 사용 시 측정 중 메시지 13번째 이후부터 버려짐. FCM collapsible 메시지 한도(기기당 연속 20개)에 걸린 것으로 추정. 사용자 승인 후 collapse_key 제거, CLAUDE.md 3장 반영
  - ◦ ZUI가 최근 앱 정리 시 앱을 강제 중지(`ZuiMemoryCleaner_Recents`)하여 메시지 18개 유실. 사용자가 최근 앱 잠금, 자동 시작 허용, 배터리 최적화 해제를 설정한 뒤 해결. CLAUDE.md 13장 반영
- 지연 측정 (켜기와 끄기 10회씩 20개, FCM 접수 시각 기준, 시계 차이 보정)
  - ◦ 화면 켜짐: 20개 모두 도착, 1개는 FCM 순서 역전으로 늦게 와서 SEQ 폐기. 중앙값 0.71초, 최대 1.22초
  - ◦ 강제 깊은 절전(deviceidle force-idle): 20개 모두 수신. 중앙값 0.81초, 최대 1.06초
  - ◦ 발송 시작부터는 중앙값 약 1.1~1.2초 (토큰 재사용 상태)
  - ◦ 측정 스크립트는 일회성이라 저장소에 넣지 않음

### □ 6단계: PC 게임 감지
- `config.py`: games는 exe 파일 이름 형식만 허용 (경로, 셸 특수 문자 거부), poll_interval 1~60초, mode 검증, %APPDATA% 확장. 비교는 소문자, 표시는 설정에 적은 표기. `config.example.json` 추가
- `providers.py`: `psutil.process_iter(["name"])`로 이름만 조회, 조회 실패는 `ProcessQueryError`로 빈 목록과 구분. 시나리오 재생용 `FakeProvider`
- `detector.py`
  - ◦ `Detector`: 게임 감지 즉시 on, 마지막 게임 종료 후 유예 4초 뒤 off, 조회 실패 시 상태 유지
  - ◦ `Bridge`: 앱 시작 시 현재 상태 발송, 상태 변경 시에만 발송, 실패 시 30초마다 현재 상태로 재발송, 감지 주기 사이 30초 이상이면 절전 해제로 보고 재발송, 다시 보내기, 일시정지(게임 중이면 off), 종료 시 off
  - ◦ 상태 표시는 FCM 접수까지만 (모드 전환 완료로 표시하지 않음)
- `sender.StateMessenger`: 상태를 새 순번의 암호화 메시지로 만들어 발송
- `__main__.py`: `run` (Windows 이름 있는 뮤텍스로 중복 실행 방지, 로그 1MB 3개 순환, Ctrl+C 시 off 발송), `list-proc [검색어]`
  - ◦ 감지 시각은 벽시계 사용. Windows의 time.monotonic은 절전 시간을 빼고 셀 수 있어 절전 해제 판단에 부적합함
- `tools/simulate.py`: multi, flapping 시나리오 추가 (가짜 프로세스 목록으로 실제 Detector와 Bridge를 거침)
- `tools/fake_game.py`: PyInstaller로 `pc/build/fake/fake_game.exe` 빌드 (build 폴더는 커밋 제외)
- 테스트: PC `pytest` 111 passed (config, providers, detector와 Bridge 규칙, simulate multi와 flapping 추가)
- 실제 프로세스 확인 (드라이런, 실제 발송 없음)
  - ◦ fake_game.exe 실행 후 약 2초 안에 on, 종료 후 유예 4초 지나 off
  - ◦ 두 번째 `run` 실행은 "이미 실행 중" 안내 후 종료
  - ◦ CPU 사용률: 60초 동안 31ms, 코어 1개 기준 약 0.05% (목표 1% 미만). 메모리 약 42MB
  - ◦ 처음 시험에서 off가 안 나온 원인: PyInstaller 단일 파일 exe가 같은 이름의 자식 프로세스를 띄우는데 부모만 종료했음 (감지기는 올바르게 on 유지). CLAUDE.md 7장에 기록
  - ◦ CPU를 처음에 0으로 잰 원인: 가상환경 python.exe는 실제 파이썬을 자식으로 띄우는 실행기임

### □ 알림 자동 삭제 제거 및 엑셀 실발송 시험
- 사용자 결정: 알림 자동 삭제 기능 필요 없음
  - ◦ `setTimeoutAfter` 제거. 새 알림 게시 전 이전 ON, OFF 알림을 지우고 새로 게시하여 마지막 상태 하나만 남김
  - ◦ 덮어쓰기(업데이트)는 루틴이 새 알림으로 감지하지 않을 수 있어 사용하지 않음. CLAUDE.md 5장 반영
- 사용자 요청: 게임 대신 MS 오피스 엑셀(`EXCEL.EXE`)로 시험. `pc/config.json`에 등록 (커밋 제외 확인), live 모드로 `run` 실행
- 결과 (시계 차이 보정, FCM 접수 기준)
  - ◦ 시작 시 현재 상태 off: 약 0.9초
  - ◦ 엑셀 실행 → on: 약 0.7초
  - ◦ 엑셀 종료 → off: 약 1.1초 (여기에 감지 주기 최대 2초와 종료 유예 4초가 더해짐)
  - ◦ 사용자가 태블릿에서 알림 표시 확인

### □ 7단계: 트레이 앱 통합
- `tray.py`: pystray 트레이 메뉴, 상태별 아이콘 색(초록 게임 중, 회색 대기, 빨강 실패, 노랑 일시정지). 감지는 별도 스레드, 창은 열 때마다 새 스레드, Bridge는 잠금으로 보호
  - ◦ 기기 미등록이나 서비스 계정 없음은 발송 실패로 표시하고 30초마다 재시도. 트레이에서 등록을 확정하면 새 키로 현재 상태를 바로 발송
- 사용자 요청: 감지할 프로그램을 json 대신 프로그램에서 지정. **감지할 프로그램 관리** 창에서 파일 탐색기로 exe를 골라 추가, 제거, 저장 즉시 감지기 반영 (8단계 항목을 당겨 구현)
- 설정 파일을 `%APPDATA%/GameModeBridge/config.json`으로 옮김 (exe 배포 대비). 기존 엑셀 설정을 이동함. 빈 감지 목록 허용, exe 이름에 유니코드 글자 허용
- 인자 없이 실행하면 트레이 앱. `GameModeBridge.exe` 빌드 (`pc/dist`, 커밋 제외, 26.4MB)
- README.md 작성 (빌드, 처음 설정, 트레이 메뉴, 시작 프로그램 등록, 문제 해결)
- 테스트: PC `pytest` 119 passed
- 실사용 확인 (사용자 확인)
  - ◦ 소스 실행 트레이: 감지 목록에 notepad.exe 추가 후 메모장 실행과 종료로 on, off 발송
  - ◦ exe 실행: 시작 시 off 발송, 태블릿 수신. keyring, DPAPI, FCM 모두 exe에서 동작. 일반 사용자 권한
- 11장 보안 점검 체크리스트 (2026-10-19)
  - ◦ 1 저장소 기록에 금지 파일 없음: 통과
  - ◦ 2 디스크에 서비스 계정 평문 없음: 통과 (38만여 파일 검사. 테스트 가짜 값과 무관한 Oracle DLL의 문자열만 발견)
  - ◦ 3 공유 키가 keyring, Keystore 외에 영구 저장 안 됨: 통과 (공유 키 발견 없음)
  - ◦ 4 서비스 계정 권한: 통과 (testIamPermissions로 시험한 10개 권한 중 cloudmessaging.messages.create만 있음)
  - ◦ 5 verify=False, 하드코딩 키, 토큰 출력, 고정 IV 없음: 통과
  - ◦ 6 stale, replay, reorder, tamper 폐기: 통과 (5단계 실발송)
  - ◦ 7 관리자 권한 없이 동작: 통과
  - ◦ 8 서비스 exported false, 릴리스에 시뮬레이터 없음: 통과
  - ◦ 9 루틴 조건에 앱 지정: 확인 불가 (갤럭시와 루틴 없음)
  - ◦ 10 pip-audit: 통과 (알려진 취약점 없음)
- 남은 완료 기준: 시작 프로그램 등록 후 재부팅 자동 실행 확인 (사용자가 직접 하기로 함)

### □ 다른 기기에 설치할 수 있게 포팅
- 사용자 결정: 대상은 다른 Windows PC와 다른 안드로이드 휴대폰, 연결 구성은 PC 1대와 휴대폰 1대 유지
- PC (개발 환경 없이 exe만으로 설치)
  - ◦ 트레이 메뉴 추가: **서비스 계정 가져오기...** (파일 탐색기로 JSON 선택, DPAPI 저장, 원본 삭제 안내), **실제 발송** 체크 (config의 mode 저장, 발송자 재생성 후 현재 상태 재발송)
  - ◦ `config.save_mode` 추가, 설정 값 하나만 바꾸는 `_update`로 정리
  - ◦ `pc/build.ps1`: 테스트 후 PyInstaller 빌드, 저장소 루트 `dist\GameModeBridge.exe`로 복사. PowerShell 5.1이 한글을 읽도록 BOM 있는 UTF-8로 저장
- 안드로이드 (서명된 APK 파일로 설치)
  - ◦ 릴리스 서명 키 생성: `%USERPROFILE%\.gamemodebridge\release.jks` (RSA 4096, PKCS12), 비밀번호는 무작위 생성하여 `android\keystore.properties`에만 기록 (커밋 제외, 출력 안 함)
  - ◦ `app/build.gradle.kts`: keystore.properties가 있을 때만 릴리스 서명
  - ◦ apksigner 검증 통과 (v2 서명). 인증서 SHA-1 `ff:ec:da:4c:8f:ba:bc:a0:18:7f:65:49:83:f4:c0:48:c7:47:82:43`
  - ◦ 처음 apksigner 결과를 통과로 보고했으나 JAVA_HOME이 없어 실제로는 출력이 비어 있었음. JAVA_HOME 지정 후 다시 검증하여 확인
- 배포 폴더 `dist\`: `GameModeBridge.exe`, `GameModeBridge.apk` (커밋 제외)
- README: 다른 PC 설치, 이전 PC 정리, 다른 휴대폰 설치, 릴리스 서명 키 백업과 SHA-1 등록 안내
- CLAUDE.md 11장: 서명 키와 비밀번호 파일, PC별 서비스 계정 키 관리 추가
- 테스트: PC `pytest` 120 passed, 안드로이드 `testDebugUnitTest` 통과, 새 exe 실행 확인
- 서명 APK 실기기 확인 (사용자 확인): 태블릿의 디버그 앱 삭제 후 APK 파일을 Download 폴더에 넣고 파일 관리자로 설치, 재등록, 알림 수신 정상 (R8 적용 릴리스 빌드에서도 동작)
- 배포 파일을 사용자 요청으로 `E:\개인앱개발\`에 복사 (`GameModeBridge.exe`, `GameModeBridge.apk`)

### □ 갤럭시 설치와 서비스 계정 키 재사용 (2026-10-20)
- 갤럭시 S25 Ultra (SM-S938N, 안드로이드 17) USB 연결
  - ◦ 증상: 알림 안 뜸. 앱이 기본 사용자 공간(user 0)에 없었음 (보안 폴더 user 150만 존재, adb 접근 불가)
  - ◦ 서명 APK를 user 0에 adb 설치, 알림 권한 허용, 배터리 최적화 예외, 백그라운드 실행 허용
  - ◦ 개발 PC에서 재등록 후 수신 확인: `끄기: 메시지 검증 완료, 알림 게시 요청 완료`
- 사용자 결정: PC마다 서비스 계정 키를 새로 발급하지 않고 JSON 1개를 모든 PC에서 재사용 (내보내기 기능 추가안 대신)
  - ◦ 원본 JSON을 지운 상태였으므로 `sa.bin`을 DPAPI로 복호화하여 `E:\개인앱개발\GameModeBridge-service-account.json`으로 복원 (내용 출력 안 함). 사용자가 exe와 함께 안전한 곳에 보관
  - ◦ 트레이 가져오기 완료 안내문 수정: 보관용 원본은 두고 PC에 복사한 사본만 삭제 안내
  - ◦ README 다른 PC 설치 절차, CLAUDE.md 저장 암호화와 11장 키 관리 문구 수정
  - ◦ exe 재빌드 (테스트 통과), `dist\`와 `E:\개인앱개발\`에 교체
- 다른 PC 설치 시험: 사용자 확인 결과 정상 동작

### □ 게임 목록 추가 기능 (2026-10-20)
- 사용자 선택: 기본 게임 목록 내장과 실행 중 프로그램에서 고르기 둘 다
- 기본 게임 목록 `config.PRESET_GAMES` (exe 이름은 커뮤니티 자료 기준, 공식 확인 아님)
  - ◦ 명조 `Client-Win64-Shipping.exe`, 오버워치 2 `Overwatch.exe`, 레식 `RainbowSix.exe` `RainbowSix_Vulkan.exe`, 배그 `TslGame.exe`, 이환 `HTGame.exe`, GTA 5 `GTA5.exe` `GTA5_Enhanced.exe`, 에이펙스 `r5apex.exe` `r5apex_dx12.exe`
  - ◦ 새 설정 파일의 기본 games로 들어감. 기존 PC는 관리 창의 **기본 게임 목록 추가** 버튼으로 합침 (중복 건너뜀)
- 관리 창에 **실행 중인 프로그램에서...** 추가: 검색, 새로고침, 여러 개 선택. 이미 목록에 있는 이름은 숨김 (`providers.running_exe_names`)
- `config.add_names` 추가, `add_games`는 이를 사용하도록 정리
- 테스트: `pytest` 124 passed, 창 버튼 자동 클릭 시험 통과, exe 재빌드 후 `E:\개인앱개발\`에 교체
- 개발 PC 설정에도 기본 게임 목록을 합침 (기존 EXCEL.EXE, notepad.exe 유지)

### □ 아이콘 변경 (2026-10-20)
- 사용자 선택: 직접 디자인 시안 승인, 트레이도 같은 모양에 상태 색 유지
- 디자인: 남색(#263859) 둥근 사각형 위 흰색 게임 패드와 신호 호 2개
- `pc/gmb/icon.py`: Pillow로 4배 크기에 그린 뒤 축소 (`app_icon`, `glyph`). 새 라이브러리 없음
  - ◦ 트레이 아이콘: 같은 모양, 배경색으로 상태 표시 (초록, 회색, 빨강, 노랑)
- `pc/tools/make_icons.py`: `pc/assets/GameModeBridge.ico`(16~256px)와 안드로이드 `mipmap-*/ic_launcher_foreground.png` 생성 (커밋함)
- 안드로이드: 적응형 아이콘 (`mipmap-anydpi-v26/ic_launcher.xml`, 배경 색 리소스, 테마 아이콘용 monochrome), 매니페스트 `icon`, `roundIcon` 지정
- `build.ps1`: PyInstaller `--icon` 추가
- 테스트: `pytest` 127 passed, 안드로이드 `testDebugUnitTest` 통과, 릴리스 APK 서명 SHA-1 기존과 같음 (업데이트 설치 가능, 재등록 불필요)
- exe와 apk를 `dist\`와 `E:\개인앱개발\`에 교체

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

### □ 7단계: 트레이 앱 통합
- 트레이 메뉴 (현재 상태, 다시 보내기, 감지 일시정지, 기기 등록, 설정 파일 열기, 종료), PyInstaller exe, 시작 프로그램 등록 안내 README
- 11장 보안 점검 체크리스트 전 항목 확인
- 사용자 할 일: `pc/config.json` 작성 (실제 게임 exe 이름은 `list-proc`로 확인), PC 시간 동기화 (선택)
- 서비스 계정 원본 JSON은 사용자가 삭제함 (2026-10-19 확인)

### □ 참고
- 새 터미널에서 `gradlew.bat`가 JDK를 못 찾으면 `JAVA_HOME` 설정 전에 열린 창이므로 새로 열면 됨
- 작업 중 요청된 `conda activate base`는 CLAUDE.md 2장 규칙(conda base 사용 금지)에 따라 실행하지 않음
