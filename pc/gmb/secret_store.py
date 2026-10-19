"""공유 키와 토픽 저장소 (CLAUDE.md 6장 저장 암호화).

keyring은 Windows 자격 증명 관리자에 저장하며 내부적으로 DPAPI로 보호됨.
키 값은 로그나 화면에 출력하지 않음.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path

import keyring
from keyring.errors import PasswordDeleteError

from gmb import crypto

SERVICE = "GameModeBridge"
_KEY_NAME = "shared_key"
_TOPIC_NAME = "topic"


@dataclass(frozen=True)
class Credentials:
    key: bytes
    topic: str

    def __repr__(self) -> str:
        # 실수로 출력되어도 키가 드러나지 않게 함
        return f"Credentials(topic={self.topic!r}, key=<숨김>)"


class KeyringSecretStore:
    def load(self) -> Credentials | None:
        key = keyring.get_password(SERVICE, _KEY_NAME)
        topic = keyring.get_password(SERVICE, _TOPIC_NAME)
        if key is None or topic is None:
            return None
        return Credentials(crypto.b64url_decode(key), topic)

    def save(self, creds: Credentials) -> None:
        keyring.set_password(SERVICE, _KEY_NAME, crypto.b64url_encode(creds.key))
        keyring.set_password(SERVICE, _TOPIC_NAME, creds.topic)

    def delete(self) -> None:
        for name in (_KEY_NAME, _TOPIC_NAME):
            try:
                keyring.delete_password(SERVICE, name)
            except PasswordDeleteError:
                pass  # 저장된 값이 없음


REQUIRED_SA_FIELDS = ("type", "project_id", "private_key", "client_email", "token_uri")


def validate_service_account(raw: bytes) -> dict:
    """서비스 계정 JSON 형식만 확인함. 오류 메시지에 값을 넣지 않음."""
    try:
        info = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("JSON 파일이 아님") from None
    if not isinstance(info, dict) or info.get("type") != "service_account":
        raise ValueError("서비스 계정 키 파일이 아님")
    missing = [f for f in REQUIRED_SA_FIELDS if not info.get(f)]
    if missing:
        raise ValueError(f"필수 항목 없음: {', '.join(missing)}")
    return info


class DpapiServiceAccountStore:
    """서비스 계정 JSON을 DPAPI로 암호화한 파일(sa.bin)로 보관함 (Windows 전용).

    DPAPI: 현재 Windows 사용자 계정으로만 풀 수 있게 잠그는 Windows 기본 암호화 기능.
    복호화한 내용은 메모리에서만 사용하고 디스크에 평문으로 쓰지 않음.
    """

    def __init__(self, path: Path):
        self.path = path

    def save(self, raw: bytes) -> None:
        import win32crypt

        validate_service_account(raw)
        blob = win32crypt.CryptProtectData(raw, "GameModeBridge SA", None, None, None, 0)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(blob)

    def load(self) -> dict:
        import win32crypt

        _, raw = win32crypt.CryptUnprotectData(self.path.read_bytes(), None, None, None, 0)
        return validate_service_account(raw)


def default_sa_path() -> Path:
    return Path(os.environ["APPDATA"]) / "GameModeBridge" / "sa.bin"


class MemorySecretStore:
    """테스트용."""

    def __init__(self, creds: Credentials | None = None):
        self.creds = creds

    def load(self) -> Credentials | None:
        return self.creds

    def save(self, creds: Credentials) -> None:
        self.creds = creds

    def delete(self) -> None:
        self.creds = None
