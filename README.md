# GameModeBridge

PC에서 지정한 프로그램(게임)이 실행되면 휴대폰의 게임 모드를 켜고, 종료되면 끄도록 신호를 보내는 개인용 도구입니다.

```
[PC 트레이 앱] 프로그램 실행 감지 → AES-256-GCM 암호화 → FCM 발송
[휴대폰 앱] 복호화 및 검증 → GAMEMODE_ON / GAMEMODE_OFF 알림 게시
[삼성 모드 및 루틴] 알림 키워드 감지 → 게임 모드 켜기 / 끄기
```

개발 지침은 `CLAUDE.md`, 진행 기록은 `WORKLOG.md`에 있습니다.

---

## PC 앱

### 빌드

`pc` 폴더에서 실행합니다.

```
.venv\Scripts\python.exe -m PyInstaller --onefile --noconsole --name GameModeBridge --paths . ^
  --hidden-import pystray._win32 --hidden-import keyring.backends.Windows ^
  --distpath dist --workpath build\pyi --specpath build gmb\__main__.py
```

결과물: `pc\dist\GameModeBridge.exe`

### 처음 설정 (한 번만)

1. 서비스 계정 키 가져오기 (FCM 발송 역할만 가진 전용 계정)
   ```
   .venv\Scripts\python.exe -m gmb import-sa <서비스 계정 JSON 경로>
   ```
   - 키는 DPAPI로 암호화되어 `%APPDATA%\GameModeBridge\sa.bin`에 저장됩니다.
   - 가져온 뒤 원본 JSON 파일은 직접 삭제하세요.
2. 휴대폰 기기 등록: 트레이 메뉴의 **기기 등록...** (또는 `python -m gmb register`)
   - 휴대폰 앱의 기기 등록 화면에서 QR을 스캔하고, 새 토픽 구독 성공이 표시되면 PC 창에서 **휴대폰 등록 완료**를 누릅니다.
3. 감지할 프로그램 지정: 트레이 메뉴의 **감지할 프로그램 관리...** → **exe 파일 추가...**
   - 게임은 런처가 아닌 실제 게임 실행 파일을 고릅니다. 이름을 모르면 게임을 실행한 상태에서 `python -m gmb list-proc 검색어` 로 확인합니다.
4. 실제 발송 모드: 트레이 메뉴의 **설정 파일 열기**에서 `"mode": "live"` 로 바꾸고 앱을 다시 실행합니다. (기본값은 발송하지 않는 `dry-run`)

### 트레이 메뉴

| 메뉴 | 동작 |
|---|---|
| 상태 | 게임 감지됨 / 대기, FCM 접수 완료 / 발송 실패 (휴대폰 도착이나 모드 전환 완료를 뜻하지 않음) |
| 현재 상태 다시 보내기 | 휴대폰과 상태가 어긋났을 때 수동으로 맞춤 |
| 감지 일시정지 | 게임 중이었다면 off를 보낸 뒤 감지를 멈춤 |
| 감지할 프로그램 관리... | 파일 탐색기로 exe 추가, 제거. 저장 즉시 반영 |
| 기기 등록... | QR 재등록 (완료를 누르기 전까지 기존 연결 유지) |
| 설정 파일 열기 | `%APPDATA%\GameModeBridge\config.json` |
| 종료 | 게임 중이었다면 off를 보낸 뒤 종료 |

아이콘 색: 초록 게임 중, 회색 대기, 빨강 발송 실패(30초마다 재시도), 노랑 일시정지

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
