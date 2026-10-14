"""PC와 안드로이드 암호화 교차 검증용 테스트 벡터를 생성함 (CLAUDE.md 7장).

고정 키와 고정 IV는 이 파일에서만 사용함. 실제 코드에서는 절대 사용하지 않음.
실행: pc 폴더에서 .venv\\Scripts\\python.exe -m tools.make_testvectors
"""

import json
from pathlib import Path

from gmb import crypto

OUTPUT = Path(__file__).resolve().parents[2] / "shared" / "testvectors" / "crypto_v1.json"

KEY = bytes(range(32))
OTHER_KEY = bytes(range(32, 64))
IV = bytes(range(12))

PAYLOADS = {
    "on_ascii": {"state": "on", "game": "VALORANT", "ts": 1760000000, "seq": 1, "msg_id": "0" * 32},
    "off_korean": {"state": "off", "game": "검은사막", "ts": 1760000060, "seq": 2, "msg_id": "f" * 32},
    "off_empty_game": {"state": "off", "game": "", "ts": 1760000120, "seq": 3, "msg_id": "a" * 32},
}


def _flip_last_byte(text: str) -> str:
    raw = bytearray(crypto.b64url_decode(text))
    raw[-1] ^= 0x01
    return crypto.b64url_encode(bytes(raw))


def build() -> dict:
    valid = []
    for name, payload in PAYLOADS.items():
        plaintext = crypto.encode_plaintext(payload)
        valid.append({
            "name": name,
            "key": crypto.b64url_encode(KEY),
            "plaintext": plaintext.decode("utf-8"),
            "envelope": crypto.seal_with_iv(KEY, IV, plaintext),
        })

    base_plain = crypto.encode_plaintext(PAYLOADS["on_ascii"])
    base_env = crypto.seal_with_iv(KEY, IV, base_plain)
    invalid = [
        {"name": "tampered_ct", "reason": "auth",
         "envelope": dict(base_env, ct=_flip_last_byte(base_env["ct"]))},
        {"name": "tampered_iv", "reason": "auth",
         "envelope": dict(base_env, iv=_flip_last_byte(base_env["iv"]))},
        {"name": "other_key", "reason": "auth",
         "envelope": crypto.seal_with_iv(OTHER_KEY, IV, base_plain)},
        {"name": "other_aad", "reason": "auth",
         "envelope": crypto.seal_with_iv(KEY, IV, base_plain, aad=b"GMB-v2")},
        {"name": "truncated_tag", "reason": "auth",
         "envelope": dict(base_env, ct=crypto.b64url_encode(crypto.b64url_decode(base_env["ct"])[:-1]))},
        {"name": "unsupported_version", "reason": "version",
         "envelope": dict(base_env, v="2")},
    ]
    for item in invalid:
        item["key"] = crypto.b64url_encode(KEY)

    return {"version": crypto.PROTOCOL_VERSION, "aad": crypto.AAD.decode("ascii"), "valid": valid, "invalid": invalid}


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"테스트 벡터 생성: {OUTPUT}")


if __name__ == "__main__":
    main()
