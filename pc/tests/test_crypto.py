import secrets

import pytest
from cryptography.exceptions import InvalidTag

from gmb import crypto

PAYLOAD = {"state": "on", "game": "VALORANT", "ts": 1760000000, "seq": 1, "msg_id": "ab" * 16}


@pytest.fixture
def key():
    return secrets.token_bytes(32)


def _flip_byte(text: str, index: int) -> str:
    raw = bytearray(crypto.b64url_decode(text))
    raw[index] ^= 0x01
    return crypto.b64url_encode(bytes(raw))


def test_round_trip(key):
    assert crypto.open_envelope(key, crypto.seal(key, PAYLOAD)) == PAYLOAD


def test_round_trip_korean_game_name(key):
    payload = dict(PAYLOAD, game="검은사막")
    assert crypto.open_envelope(key, crypto.seal(key, payload)) == payload


def test_envelope_has_only_three_fields(key):
    assert set(crypto.seal(key, PAYLOAD)) == {"v", "iv", "ct"}


def test_iv_differs_per_message(key):
    ivs = {crypto.seal(key, PAYLOAD)["iv"] for _ in range(100)}
    assert len(ivs) == 100


def test_iv_is_12_bytes(key):
    assert len(crypto.b64url_decode(crypto.seal(key, PAYLOAD)["iv"])) == 12


@pytest.mark.parametrize("index", [0, -1])
def test_tampered_ciphertext_rejected(key, index):
    env = crypto.seal(key, PAYLOAD)
    env["ct"] = _flip_byte(env["ct"], index)
    with pytest.raises(InvalidTag):
        crypto.open_envelope(key, env)


def test_tampered_iv_rejected(key):
    env = crypto.seal(key, PAYLOAD)
    env["iv"] = _flip_byte(env["iv"], 0)
    with pytest.raises(InvalidTag):
        crypto.open_envelope(key, env)


def test_wrong_key_rejected(key):
    env = crypto.seal(key, PAYLOAD)
    with pytest.raises(InvalidTag):
        crypto.open_envelope(secrets.token_bytes(32), env)


def test_wrong_aad_rejected(key):
    env = crypto.seal_with_iv(key, secrets.token_bytes(12), crypto.encode_plaintext(PAYLOAD), aad=b"GMB-v2")
    with pytest.raises(InvalidTag):
        crypto.open_envelope(key, env)


def test_unsupported_version_rejected(key):
    env = dict(crypto.seal(key, PAYLOAD), v="2")
    with pytest.raises(ValueError):
        crypto.open_envelope(key, env)


@pytest.mark.parametrize("size", [16, 31, 33])
def test_wrong_key_size_rejected(size):
    with pytest.raises(ValueError):
        crypto.seal(b"\x00" * size, PAYLOAD)


def test_sync_field_only_when_requested():
    assert "sync" not in crypto.make_payload("off", "", 1, 100)
    assert crypto.make_payload("off", "", 1, 100, sync=True)["sync"] is True
