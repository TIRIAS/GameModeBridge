"""가짜 게임 프로세스 (CLAUDE.md 7장). 실제 게임 없이 감지 경로를 검증하기 위함.

빌드: pc 폴더에서 .venv\\Scripts\\python.exe -m PyInstaller --onefile --name fake_game --distpath build\\fake tools\\fake_game.py
실행: build\\fake\\fake_game.exe [초]  (지정한 시간 뒤 또는 Ctrl+C로 종료)
"""

import sys
import time

seconds = float(sys.argv[1]) if len(sys.argv) > 1 else float("inf")
print(f"fake_game 실행 중 ({'무한' if seconds == float('inf') else f'{seconds:.0f}초'})")
try:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        time.sleep(0.5)
except KeyboardInterrupt:
    pass
print("fake_game 종료")
