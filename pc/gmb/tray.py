"""트레이 UI (CLAUDE.md 7단계, Windows 전용).

트레이 메뉴는 pystray가 주 스레드에서, 감지는 별도 스레드에서, 창(tkinter)은 열 때마다 새 스레드에서 실행함.
감지 상태(Bridge)는 잠금으로 보호함.
"""

import logging
import os
import threading
import time
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

from gmb import config as config_mod
from gmb import registration, state_store
from gmb.detector import Bridge, Detector
from gmb.providers import PsutilProvider
from gmb.secret_store import DpapiServiceAccountStore, KeyringSecretStore, default_sa_path
from gmb.sender import DryRunSender, FcmSender, SendError, StateMessenger

log = logging.getLogger(__name__)

_COLORS = {"on": (46, 160, 67), "off": (128, 128, 128), "error": (218, 54, 51), "paused": (219, 171, 9)}


def _icon_image(kind: str) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((4, 16, 60, 48), radius=14, fill=_COLORS[kind])
    d.rectangle((14, 29, 26, 35), fill="white")
    d.rectangle((17, 26, 23, 38), fill="white")
    d.ellipse((40, 24, 46, 30), fill="white")
    d.ellipse((46, 32, 52, 38), fill="white")
    return img


class _Unavailable:
    """발송 준비가 안 된 경우 (기기 미등록, 서비스 계정 없음). Bridge가 실패로 표시하고 30초마다 다시 시도함."""

    def __init__(self, reason: str):
        self.reason = reason

    def send(self, topic, envelope):
        raise SendError(self.reason)


class App:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.cfg = config_mod.load_or_create(config_path)
        self.secrets = KeyringSecretStore()
        self.states = state_store.FileStateStore(state_store.default_path())
        self.messenger = StateMessenger(self.secrets.load(), self.states, self._make_sender())
        self.bridge = Bridge(PsutilProvider(), Detector(self.cfg.games), self._send_state)
        self.lock = threading.RLock()
        self.window_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.icon = pystray.Icon("GameModeBridge", _icon_image("off"), "GameModeBridge", self._menu())

    # ---------- 발송 ----------

    def _make_sender(self):
        if self.cfg.mode != "live":
            return DryRunSender(Path(os.environ["APPDATA"]) / "GameModeBridge" / "dryrun.log")
        sa_path = self.cfg.sa_store_path or default_sa_path()
        if not sa_path.exists():
            return _Unavailable("서비스 계정 없음 (import-sa 필요)")
        return FcmSender(DpapiServiceAccountStore(sa_path).load())

    def _send_state(self, state: str, game: str) -> None:
        if self.messenger.creds is None:
            raise SendError("기기 미등록")
        self.messenger(state, game)

    # ---------- 감지 스레드 ----------

    def _loop(self) -> None:
        while not self.stop_event.is_set():
            with self.lock:
                self.bridge.tick(time.time())  # 벽시계: 절전 해제 판단용
            self._refresh()
            self.stop_event.wait(self.cfg.poll_interval_sec)

    def _refresh(self) -> None:
        b = self.bridge
        kind = "paused" if b.paused else "error" if b.unsent else "on" if b.desired == "on" else "off"
        self.icon.icon = _icon_image(kind)
        self.icon.title = f"GameModeBridge: {b.status}"[:127]
        self.icon.update_menu()

    # ---------- 메뉴 ----------

    def _menu(self) -> pystray.Menu:
        item = pystray.MenuItem
        mode = "실제 발송" if self.cfg.mode == "live" else "드라이런 (발송 안 함)"
        return pystray.Menu(
            item(lambda _: f"상태: {self.bridge.status}", None, enabled=False),
            item(lambda _: f"감지 대상 {len(self.bridge.detector.games)}개 / {mode}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            item("현재 상태 다시 보내기", self._on_resend),
            item("감지 일시정지", self._on_toggle_pause, checked=lambda _: self.bridge.paused),
            item("감지할 프로그램 관리...", self._on_games),
            item("기기 등록...", self._on_register),
            item("설정 파일 열기", lambda: os.startfile(self.config_path)),
            pystray.Menu.SEPARATOR,
            item("종료", self._on_quit),
        )

    def _on_resend(self) -> None:
        with self.lock:
            self.bridge.resend_current()

    def _on_toggle_pause(self) -> None:
        with self.lock:
            if self.bridge.paused:
                self.bridge.resume()
            else:
                self.bridge.pause(time.time())
        self._refresh()

    def _on_quit(self) -> None:
        self.stop_event.set()
        with self.lock:
            self.bridge.shutdown(time.time())  # 게임 중이었다면 off 발송
        self.icon.stop()

    def _open_window(self, target) -> None:
        """창은 한 번에 하나만 엶. tkinter는 창을 만든 스레드에서만 다룸."""
        if not self.window_lock.acquire(blocking=False):
            return

        def run():
            try:
                target()
            except Exception:
                log.exception("창 처리 중 오류")
            finally:
                self.window_lock.release()
                self._refresh()

        threading.Thread(target=run, daemon=True).start()

    def _on_register(self) -> None:
        def run():
            flow = registration.RegistrationFlow(self.secrets, self.states)
            if registration.show_window(flow):
                creds = flow.pending
                flow.confirm()
                with self.lock:
                    # 새 키로 현재 상태를 보내야 휴대폰이 새 등록을 확정함 (CLAUDE.md 6장 재등록)
                    self.messenger.creds = creds
                    self.bridge.resend_current()
                log.info("기기 등록 확정")
            else:
                flow.cancel()

        self._open_window(run)

    def _on_games(self) -> None:
        self._open_window(lambda: show_games_window(self))

    def apply_games(self, games: list[str]) -> None:
        self.cfg = config_mod.save_games(self.config_path, games)
        with self.lock:
            self.bridge.detector.set_games(self.cfg.games)
        log.info("감지 목록 변경: %d개", len(self.cfg.games))

    def run(self) -> None:
        def setup(icon):
            # pystray가 아이콘을 띄운 뒤 별도 스레드에서 호출함
            icon.visible = True
            self._loop()

        self.icon.run(setup=setup)


def show_games_window(app: App) -> None:
    """감지할 프로그램 관리 창. 파일 탐색기로 exe를 골라 추가함."""
    import tkinter as tk
    from tkinter import filedialog, messagebox

    games = list(app.cfg.games)
    root = tk.Tk()
    root.title("감지할 프로그램 관리")
    root.attributes("-topmost", True)

    tk.Label(root, justify="left", text=(
        "실행되면 휴대폰 게임 모드를 켤 프로그램입니다.\n"
        "게임은 런처가 아닌 실제 게임 실행 파일을 고르세요 (예: 게임 폴더 안의 ...Win64-Shipping.exe).\n"
        "파일 이름으로만 비교하므로 다른 폴더의 같은 이름 프로그램도 감지됩니다."
    )).pack(padx=16, pady=(16, 8), anchor="w")

    listbox = tk.Listbox(root, width=50, height=10, selectmode="extended")
    listbox.pack(padx=16, fill="both", expand=True)

    def refresh():
        listbox.delete(0, "end")
        for g in games:
            listbox.insert("end", g)

    def add():
        paths = filedialog.askopenfilenames(parent=root, title="감지할 exe 파일 선택",
                                            filetypes=[("실행 파일", "*.exe")])
        if not paths:
            return
        new, rejected = config_mod.add_games(games, list(paths))
        games[:] = new
        refresh()
        if rejected:
            messagebox.showwarning("추가하지 못한 파일", "지원하지 않는 이름입니다:\n" + "\n".join(rejected), parent=root)

    def remove():
        for i in reversed(listbox.curselection()):
            del games[i]
        refresh()

    def save():
        try:
            app.apply_games(games)
        except config_mod.ConfigError as e:
            messagebox.showerror("저장 실패", str(e), parent=root)
            return
        root.destroy()

    buttons = tk.Frame(root)
    buttons.pack(padx=16, pady=16, fill="x")
    tk.Button(buttons, text="exe 파일 추가...", command=add).pack(side="left")
    tk.Button(buttons, text="선택 항목 제거", command=remove).pack(side="left", padx=8)
    tk.Button(buttons, text="취소", command=root.destroy).pack(side="right")
    tk.Button(buttons, text="저장", command=save).pack(side="right", padx=8)

    refresh()
    root.mainloop()


def main(config_path: Path | None = None) -> None:
    App(config_path or config_mod.default_path()).run()
