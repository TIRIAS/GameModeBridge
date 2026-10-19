import re

from gmb import crypto, registration
from gmb.secret_store import Credentials, MemorySecretStore
from gmb.state_store import FileStateStore

QR_PATTERN = re.compile(r"^GMB1:gmb_[A-Za-z0-9]{16}:[A-Za-z0-9_-]{43}$")


def _old():
    return Credentials(b"\x01" * 32, "gmb_" + "a" * 16)


def test_generated_credentials_format():
    creds = registration.generate_credentials()
    assert len(creds.key) == 32
    assert re.fullmatch(r"gmb_[A-Za-z0-9]{16}", creds.topic)


def test_generated_credentials_are_random():
    a, b = registration.generate_credentials(), registration.generate_credentials()
    assert a.key != b.key and a.topic != b.topic


def test_qr_text_format_and_round_trip():
    creds = registration.generate_credentials()
    text = registration.qr_text(creds)
    assert QR_PATTERN.fullmatch(text)
    prefix, topic, key = text.split(":")
    assert (topic, crypto.b64url_decode(key)) == (creds.topic, creds.key)


def test_repr_hides_key():
    creds = Credentials(b"\xab" * 32, "gmb_x")
    assert crypto.b64url_encode(creds.key) not in repr(creds)
    assert "ab" * 4 not in repr(creds)


def test_confirm_saves_new_credentials_and_resets_seq(tmp_path):
    secrets_ = MemorySecretStore(_old())
    state = FileStateStore(tmp_path / "state.json")
    state.next_seq()
    state.next_seq()
    flow = registration.RegistrationFlow(secrets_, state)
    pending = flow.pending
    flow.confirm()
    assert secrets_.load() == pending
    assert state.last_seq() == 0


def test_pending_is_not_saved_before_confirm(tmp_path):
    secrets_ = MemorySecretStore(_old())
    registration.RegistrationFlow(secrets_, FileStateStore(tmp_path / "s.json"))
    assert secrets_.load() == _old()


def test_cancel_keeps_existing_credentials_and_seq(tmp_path):
    secrets_ = MemorySecretStore(_old())
    state = FileStateStore(tmp_path / "state.json")
    state.next_seq()
    flow = registration.RegistrationFlow(secrets_, state)
    flow.cancel()
    assert secrets_.load() == _old()
    assert state.last_seq() == 1


def test_revoke_deletes_existing_immediately(tmp_path):
    secrets_ = MemorySecretStore(_old())
    flow = registration.RegistrationFlow(secrets_, FileStateStore(tmp_path / "s.json"), revoke=True)
    assert secrets_.load() is None
    flow.cancel()
    assert secrets_.load() is None
