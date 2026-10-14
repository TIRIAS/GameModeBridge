import json

import pytest
from cryptography.exceptions import InvalidTag

from gmb import crypto
from tools import make_testvectors


def test_committed_file_matches_generator():
    # 저장된 파일이 현재 생성 코드와 같아야 안드로이드 교차 검증이 의미 있음
    committed = json.loads(make_testvectors.OUTPUT.read_text(encoding="utf-8"))
    assert committed == make_testvectors.build()


@pytest.mark.parametrize("item", make_testvectors.build()["valid"], ids=lambda i: i["name"])
def test_valid_vectors_decrypt(item):
    key = crypto.b64url_decode(item["key"])
    assert crypto.open_envelope(key, item["envelope"]) == json.loads(item["plaintext"])


@pytest.mark.parametrize("item", make_testvectors.build()["invalid"], ids=lambda i: i["name"])
def test_invalid_vectors_rejected(item):
    key = crypto.b64url_decode(item["key"])
    expected = ValueError if item["reason"] == "version" else InvalidTag
    with pytest.raises(expected):
        crypto.open_envelope(key, item["envelope"])
