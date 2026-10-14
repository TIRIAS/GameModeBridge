"""AES-256-GCM 암호화 및 메시지 봉투 생성 (CLAUDE.md 5장, 6장)."""

import base64
import json
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PROTOCOL_VERSION = "1"
AAD = b"GMB-v1"
KEY_SIZE = 32
IV_SIZE = 12


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _check_key(key: bytes) -> None:
    if len(key) != KEY_SIZE:
        raise ValueError("공유 키는 32바이트여야 함")


def encode_plaintext(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def seal_with_iv(key: bytes, iv: bytes, plaintext: bytes, aad: bytes = AAD) -> dict:
    """지정한 IV로 봉투를 만듦. 고정 IV는 테스트 벡터 생성에서만 사용함."""
    _check_key(key)
    if len(iv) != IV_SIZE:
        raise ValueError("IV는 12바이트여야 함")
    ct = AESGCM(key).encrypt(iv, plaintext, aad)
    return {"v": PROTOCOL_VERSION, "iv": b64url_encode(iv), "ct": b64url_encode(ct)}


def seal(key: bytes, payload: dict) -> dict:
    """평문 dict를 암호화하여 FCM 데이터 페이로드용 봉투를 만듦. IV는 매번 새로 생성함."""
    return seal_with_iv(key, secrets.token_bytes(IV_SIZE), encode_plaintext(payload))


def open_envelope(key: bytes, envelope: dict) -> dict:
    """봉투를 복호화하여 평문 dict를 돌려줌. 시뮬레이터와 테스트용.

    버전이 다르면 ValueError, 위변조나 다른 키이면 cryptography.exceptions.InvalidTag를 발생시킴.
    """
    _check_key(key)
    if envelope.get("v") != PROTOCOL_VERSION:
        raise ValueError("지원하지 않는 봉투 버전")
    iv = b64url_decode(envelope["iv"])
    plaintext = AESGCM(key).decrypt(iv, b64url_decode(envelope["ct"]), AAD)
    return json.loads(plaintext.decode("utf-8"))
