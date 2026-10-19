"""QR 기기 등록 (CLAUDE.md 6장 기기 등록, QR 형식, 재등록).

일반 재등록: 새 정보는 창이 열려 있는 동안 메모리에만 두고, 사용자가 완료를 눌러야 keyring에 확정함.
유출 대응 재등록(--revoke): 기존 키와 토픽을 먼저 삭제함.
"""

import secrets
import string

from gmb import crypto
from gmb.secret_store import Credentials

QR_PREFIX = "GMB1"
TOPIC_PREFIX = "gmb_"
TOPIC_RANDOM_LEN = 16
_TOPIC_ALPHABET = string.ascii_letters + string.digits
QR_VISIBLE_SEC = 60


def generate_credentials() -> Credentials:
    topic = TOPIC_PREFIX + "".join(secrets.choice(_TOPIC_ALPHABET) for _ in range(TOPIC_RANDOM_LEN))
    return Credentials(secrets.token_bytes(crypto.KEY_SIZE), topic)


def qr_text(creds: Credentials) -> str:
    return f"{QR_PREFIX}:{creds.topic}:{crypto.b64url_encode(creds.key)}"


class RegistrationFlow:
    """등록 절차의 상태 변화만 담당함. 화면은 tray/명령에서 따로 붙임."""

    def __init__(self, secret_store, state_store, revoke: bool = False):
        self.secret_store = secret_store
        self.state_store = state_store
        if revoke:
            secret_store.delete()
        self.pending = generate_credentials()

    def confirm(self) -> None:
        """휴대폰에서 새 토픽 구독 성공을 확인한 뒤 사용자가 완료를 누르면 호출함."""
        self.secret_store.save(self.pending)
        self.state_store.reset()
        self.pending = None

    def cancel(self) -> None:
        """완료 없이 창을 닫으면 새 정보를 버리고 기존 키를 유지함."""
        self.pending = None


def show_window(flow: RegistrationFlow) -> bool:
    """QR 창을 띄우고 사용자가 완료를 눌렀으면 True. Windows 화면이 있는 환경에서만 사용함."""
    import tkinter as tk

    import qrcode
    from PIL import ImageTk

    text = qr_text(flow.pending)
    root = tk.Tk()
    root.title("GameModeBridge 기기 등록")
    root.attributes("-topmost", True)
    result = {"confirmed": False}

    tk.Label(root, text="휴대폰 앱의 기기 등록 화면에서 QR을 스캔하세요.\n다른 사람이 보지 않는 곳에서 진행하세요.",
             justify="center").pack(padx=16, pady=(16, 8))

    photo = ImageTk.PhotoImage(qrcode.make(text, box_size=8, border=2).get_image())
    qr_label = tk.Label(root, image=photo)
    qr_label.pack(padx=16)
    text_label = tk.Label(root, text="", font=("Consolas", 10))
    text_label.pack(padx=16)
    timer_label = tk.Label(root, text="")
    timer_label.pack(pady=(4, 0))

    def hide_secret():
        # QR 창 노출을 줄이기 위한 것이며 QR 정보 자체가 만료되는 것은 아님
        qr_label.config(image="", text="(QR 숨김. 다시 보려면 등록을 다시 시작하세요)")
        text_label.config(text="")
        show_text_btn.config(state="disabled")

    remaining = {"sec": QR_VISIBLE_SEC}

    def tick():
        if remaining["sec"] <= 0:
            timer_label.config(text="")
            hide_secret()
            return
        timer_label.config(text=f"{remaining['sec']}초 후 QR을 숨깁니다")
        remaining["sec"] -= 1
        root.after(1000, tick)

    def show_text():
        text_label.config(text=text)

    def on_confirm():
        result["confirmed"] = True
        root.destroy()

    buttons = tk.Frame(root)
    buttons.pack(pady=16)
    show_text_btn = tk.Button(buttons, text="문자열 보기 (직접 입력용)", command=show_text)
    show_text_btn.pack(side="left", padx=4)
    tk.Button(buttons, text="휴대폰 등록 완료", command=on_confirm).pack(side="left", padx=4)
    tk.Button(buttons, text="취소", command=root.destroy).pack(side="left", padx=4)
    tk.Label(root, text="휴대폰에 새 토픽 구독 성공이 표시된 뒤 완료를 누르세요.").pack(pady=(0, 16))

    tick()
    root.mainloop()
    return result["confirmed"]
