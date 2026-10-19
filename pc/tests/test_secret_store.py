import json
import sys

import pytest

from gmb import secret_store

# 실제 키가 아닌 형식 확인용 가짜 값
FAKE_SA = {
    "type": "service_account",
    "project_id": "gamemodebridge",
    "private_key": "-----BEGIN PRIVATE KEY-----\nfake\n-----END PRIVATE KEY-----\n",
    "client_email": "gmb-sender@gamemodebridge.iam.gserviceaccount.com",
    "token_uri": "https://oauth2.googleapis.com/token",
}


def raw(d):
    return json.dumps(d).encode("utf-8")


def test_valid_service_account():
    assert secret_store.validate_service_account(raw(FAKE_SA))["client_email"] == FAKE_SA["client_email"]


@pytest.mark.parametrize("data", [
    b"not json",
    b"[]",
    raw(dict(FAKE_SA, type="authorized_user")),
    raw({k: v for k, v in FAKE_SA.items() if k != "private_key"}),
    raw(dict(FAKE_SA, client_email="")),
])
def test_invalid_service_account_rejected(data):
    with pytest.raises(ValueError):
        secret_store.validate_service_account(data)


def test_error_message_does_not_include_values():
    with pytest.raises(ValueError) as e:
        secret_store.validate_service_account(raw(dict(FAKE_SA, client_email="")))
    assert "fake" not in str(e.value)


@pytest.mark.skipif(sys.platform != "win32", reason="DPAPI는 Windows 전용")
def test_dpapi_round_trip_and_no_plaintext_on_disk(tmp_path):
    path = tmp_path / "sa.bin"
    store = secret_store.DpapiServiceAccountStore(path)
    store.save(raw(FAKE_SA))
    on_disk = path.read_bytes()
    assert b"private_key" not in on_disk and b"gmb-sender" not in on_disk
    assert store.load() == FAKE_SA


@pytest.mark.skipif(sys.platform != "win32", reason="DPAPI는 Windows 전용")
def test_dpapi_refuses_invalid_json(tmp_path):
    with pytest.raises(ValueError):
        secret_store.DpapiServiceAccountStore(tmp_path / "sa.bin").save(b"{}")
    assert not (tmp_path / "sa.bin").exists()
