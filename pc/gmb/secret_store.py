"""공유 키와 토픽 저장소 (CLAUDE.md 6장 저장 암호화).

keyring은 Windows 자격 증명 관리자에 저장하며 내부적으로 DPAPI로 보호됨.
키 값은 로그나 화면에 출력하지 않음.
"""

from dataclasses import dataclass

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
