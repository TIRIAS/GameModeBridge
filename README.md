# GameModeBridge

PC에서 지정한 프로그램(게임)이 실행되면 휴대폰의 게임 모드를 켜고, 종료되면 끄도록 신호를 보내는 개인용 도구입니다.

```
[PC 트레이 앱] 프로그램 실행 감지 → AES-256-GCM 암호화 → FCM 발송
[휴대폰 앱] 복호화 및 검증 → GAMEMODE_ON / GAMEMODE_OFF 알림 게시
[삼성 모드 및 루틴] 알림 키워드 감지 → 게임 모드 켜기 / 끄기
```

개발 지침은 `CLAUDE.md`, 진행 기록은 `WORKLOG.md`에 있습니다.

---

## 배포 파일 빌드 (개발 PC)

| 대상 | 명령 | 결과물 |
|---|---|---|
| PC exe | `pc` 폴더에서 `powershell -ExecutionPolicy Bypass -File build.ps1` (테스트 후 PyInstaller 빌드) | `dist\GameModeBridge.exe` |
| 휴대폰 APK | `android` 폴더에서 `gradlew.bat testDebugUnitTest assembleRelease` | `android\app\build\outputs\apk\release\app-release.apk` (`dist\GameModeBridge.apk`로 복사) |

APK 서명에는 아래 "릴리스 서명 키"가 필요합니다. 없으면 서명되지 않은 APK가 만들어져 설치할 수 없습니다.

---

## 다른 기기에 설치

연결 구성은 PC 1대와 휴대폰 1대입니다. 다른 PC로 옮기면 새 PC에서 기기 등록을 다시 하며, 그 순간부터 이전 PC의 신호는 휴대폰이 폐기합니다.
배포 폴더 `dist\` 에 `GameModeBridge.exe` (PC)와 `GameModeBridge.apk` (휴대폰)가 있습니다. 두 파일 모두 비밀 정보를 담고 있지 않습니다.

### 다른 Windows PC (개발 환경 불필요)

1. `GameModeBridge.exe`를 원하는 위치에 복사하고 실행합니다.
   - 서명되지 않은 exe라 Windows SmartScreen 경고가 뜨면 **추가 정보 → 실행**을 누릅니다.
   - 관리자 권한은 필요 없습니다.
2. 보관해 둔 서비스 계정 키 JSON (`GameModeBridge-service-account.json`)을 준비합니다.
   - 모든 PC가 같은 키 하나를 함께 씁니다 (사용자 결정, 2026-10-20). 키 파일은 exe와 함께 안전한 곳에 보관합니다.
   - 키 파일을 잃어버렸을 때만 Google Cloud 콘솔 → IAM 및 관리자 → 서비스 계정 → `gmb-sender` → **키** 탭 → **키 추가 → 새 키 만들기 → JSON** 으로 새로 받습니다.
3. 트레이 메뉴 **서비스 계정 가져오기...** 에서 그 JSON을 고릅니다. 새 PC에 복사본을 남기지 말고, 보관 장소의 원본은 그대로 둡니다.
4. 트레이 메뉴 **기기 등록...** 으로 휴대폰을 등록합니다.
5. 트레이 메뉴 **감지할 프로그램 관리...** 에서 목록을 확인합니다. 새 PC는 기본 게임 목록(명조, 오버워치 2, 레식, 배그, 이환, GTA 5, 에이펙스)이 이미 들어 있습니다. 다른 게임은 게임을 켠 상태에서 **실행 중인 프로그램에서...** 로 추가합니다.
6. 트레이 메뉴 **실제 발송** 을 체크합니다. (새 설정 파일은 발송하지 않는 드라이런으로 시작함)
7. 필요하면 시작 프로그램에 등록합니다 (아래 "Windows 시작 시 자동 실행").

### 이전 PC 정리

1. 트레이에서 종료하고 exe를 삭제합니다.
2. `%APPDATA%\GameModeBridge` 폴더를 삭제합니다 (설정, 암호화된 서비스 계정 키, 로그).
3. 제어판 → 자격 증명 관리자 → Windows 자격 증명에서 `GameModeBridge` 항목을 삭제합니다 (공유 키, 토픽).
4. 키는 모든 PC가 함께 쓰므로 삭제하지 않습니다. 키 파일 유출이 의심될 때만 Google Cloud 콘솔에서 그 키를 삭제하고 새로 받아 모든 PC에서 다시 가져옵니다.

### 다른 안드로이드 휴대폰 (갤럭시 등)

1. `GameModeBridge.apk`를 휴대폰으로 옮깁니다 (USB 파일 전송, 클라우드 드라이브, 메신저 내게 보내기 등).
2. 휴대폰에서 파일을 열어 설치합니다. 출처를 알 수 없는 앱 설치 허용을 물으면 그 앱(파일 관리자 등)에만 허용합니다.
3. 앱 실행 → 알림 권한 허용 → **배터리 최적화 설정 열기**에서 제한 없음으로 설정합니다.
4. 앱의 **기기 등록** → **QR 스캔** 으로 PC 트레이의 기기 등록 QR을 스캔합니다.
5. 갤럭시라면 아래 "삼성 루틴" 두 개를 만듭니다.
6. Google Play 서비스가 있어야 동작합니다 (FCM 수신, QR 스캐너).

같은 휴대폰에 디버그 빌드가 설치되어 있으면 서명이 달라 업데이트 설치가 되지 않습니다. 디버그 빌드를 삭제한 뒤 설치하고 기기 등록을 다시 합니다.

### 릴리스 서명 키 (개발 PC)

- 서명 키: `%USERPROFILE%\.gamemodebridge\release.jks`, 비밀번호: `android\keystore.properties` (둘 다 커밋하지 않음)
- 이 두 파일이 없으면 같은 앱으로 업데이트할 수 없습니다 (휴대폰에서 삭제 후 재설치와 재등록 필요). 두 파일을 함께 안전한 곳에 백업합니다.
- 인증서 지문 (공개 값): SHA-1 `ff:ec:da:4c:8f:ba:bc:a0:18:7f:65:49:83:f4:c0:48:c7:47:82:43`
- Firebase 콘솔 → 프로젝트 설정 → 내 앱 → **SHA 인증서 지문 추가**에 위 SHA-1을 등록하고, Google Cloud 콘솔의 Android API 키를 패키지 이름 `com.gamemodebridge`와 이 지문으로 제한합니다 (CLAUDE.md 11장 최소 권한)

---

## PC 앱 사용

### 처음 설정 (개발 PC, 소스로 실행할 때)

1. 서비스 계정 키 가져오기: 트레이 메뉴 **서비스 계정 가져오기...** 또는
   ```
   .venv\Scripts\python.exe -m gmb import-sa <서비스 계정 JSON 경로>
   ```
   - 키는 DPAPI로 암호화되어 `%APPDATA%\GameModeBridge\sa.bin`에 저장됩니다. 가져온 뒤 원본 JSON 파일은 직접 삭제하세요.
2. 휴대폰 기기 등록: 트레이 메뉴 **기기 등록...** (또는 `python -m gmb register`)
   - 휴대폰 앱의 기기 등록 화면에서 QR을 스캔하고, 새 토픽 구독 성공이 표시되면 PC 창에서 **휴대폰 등록 완료**를 누릅니다.
3. 감지할 프로그램 지정: 트레이 메뉴 **감지할 프로그램 관리...** → **exe 파일 추가...**
   - 게임은 런처가 아닌 실제 게임 실행 파일을 고릅니다. 이름을 모르면 게임을 실행한 상태에서 `python -m gmb list-proc 검색어` 로 확인합니다.
4. 트레이 메뉴 **실제 발송** 을 체크합니다. (기본값은 발송하지 않는 드라이런)

### 트레이 메뉴

| 메뉴 | 동작 |
|---|---|
| 상태 | 게임 감지됨 / 대기, FCM 접수 완료 / 발송 실패 (휴대폰 도착이나 모드 전환 완료를 뜻하지 않음) |
| 현재 상태 다시 보내기 | 휴대폰과 상태가 어긋났을 때 수동으로 맞춤 |
| 감지 일시정지 | 게임 중이었다면 off를 보낸 뒤 감지를 멈춤 |
| 감지할 프로그램 관리... | exe 파일 추가 (파일 탐색기), 실행 중인 프로그램에서 추가 (검색 가능), 기본 게임 목록 추가, 제거. 저장 즉시 반영 |
| 기기 등록... | QR 재등록 (완료를 누르기 전까지 기존 연결 유지) |
| 서비스 계정 가져오기... | 서비스 계정 키 JSON을 골라 DPAPI로 암호화 저장 |
| 실제 발송 | 체크하면 FCM으로 실제 발송, 해제하면 드라이런(기록만) |
| 설정 파일 열기 | `%APPDATA%\GameModeBridge\config.json` |
| 종료 | 게임 중이었다면 off를 보낸 뒤 종료 |

아이콘 배경색: 초록 게임 중, 회색 대기, 빨강 발송 실패(30초마다 재시도), 노랑 일시정지

아이콘 모양을 바꾸려면 `pc/gmb/icon.py`를 고친 뒤 `pc` 폴더에서 `.venv\Scripts\python.exe tools\make_icons.py`를 실행하고 exe와 APK를 다시 빌드합니다.

### Windows 시작 시 자동 실행

1. `GameModeBridge.exe`를 계속 둘 위치로 복사합니다. 예: `%LOCALAPPDATA%\Programs\GameModeBridge\GameModeBridge.exe`
2. `Win + R` → `shell:startup` 입력 → 열린 시작프로그램 폴더에 위 exe의 바로 가기를 만듭니다.
3. 관리자 권한 없이 일반 사용자로 실행됩니다. 관리자 권한으로 실행하도록 설정하지 마세요.

### 파일 위치

| 파일 | 내용 |
|---|---|
| `%APPDATA%\GameModeBridge\config.json` | 감지 목록, 감지 주기, 모드 |
| `%APPDATA%\GameModeBridge\sa.bin` | 서비스 계정 키 (DPAPI 암호화) |
| `%APPDATA%\GameModeBridge\state.json` | 발송 순번 (비밀 아님) |
| `%APPDATA%\GameModeBridge\logs\gamemode.log` | 로그 (1MB씩 3개 순환) |
| Windows 자격 증명 관리자 `GameModeBridge` | 공유 키와 토픽 |

---

## 휴대폰 앱

`android` 폴더에서 실행합니다. `app/google-services.json`이 필요합니다 (커밋하지 않음).

```
gradlew.bat testDebugUnitTest   # JVM 단위 테스트
gradlew.bat installDebug        # 연결된 기기에 디버그 빌드 설치 (시뮬레이터 포함)
gradlew.bat assembleRelease     # 릴리스 빌드 (R8, 시뮬레이터 제외)
```

### 휴대폰 설정

- 알림 권한 허용
- 배터리 사용량 제한 없음 (앱의 **배터리 최적화 설정 열기**)
- 중국 내수용 ROM(Lenovo ZUI 등): 최근 앱 화면에서 앱 잠금, 자동 시작 허용. 최근 앱에서 지우면 강제 중지되어 신호를 받지 못함
- PC가 갑자기 꺼져 게임 모드가 남았다면 앱의 **수동 게임 모드 끄기**를 누릅니다

### 삼성 루틴 (갤럭시)

- 루틴 1: 알림 수신 → 앱 **GameModeBridge** (반드시 지정) → 키워드 `GAMEMODE_ON` → 게임 모드 켜기
- 루틴 2: 알림 수신 → 앱 **GameModeBridge** (반드시 지정) → 키워드 `GAMEMODE_OFF` → 게임 모드 끄기
- 두 루틴 모두 루틴 종료 시 원래대로 돌리기 옵션을 해제합니다

---

## 문제 해결

| 증상 | 확인할 것 |
|---|---|
| 트레이 아이콘이 빨강 | 상태 메뉴의 사유 확인. 기기 미등록, 서비스 계정 없음, 인터넷 연결 |
| PC는 접수 완료인데 휴대폰 알림 없음 | 휴대폰 인터넷, 배터리 제한, 앱 강제 중지 여부. 휴대폰 앱의 마지막 처리 결과 확인 |
| 휴대폰에 폐기: STALE / FUTURE | PC와 휴대폰 시계 차이. 양쪽 모두 자동 시간 동기화 사용 |
| 휴대폰에 폐기: TOPIC / AUTH | 재등록 후 이전 키로 보낸 메시지. 트레이에서 기기 등록을 다시 진행 |
| 이미 실행 중이라며 꺼짐 | 다른 GameModeBridge가 실행 중. 트레이 아이콘에서 종료 후 다시 실행 |
