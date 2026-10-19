"""진입점. 사용: python -m gmb register [--revoke] | import-sa <서비스 계정 JSON 경로>"""

import argparse
import sys
from pathlib import Path

from gmb import registration, state_store
from gmb.secret_store import DpapiServiceAccountStore, KeyringSecretStore, default_sa_path, validate_service_account


def cmd_register(args) -> None:
    store = KeyringSecretStore()
    existing = store.load() is not None
    if args.revoke:
        print("기존 키와 토픽을 삭제했습니다. 등록을 마칠 때까지 휴대폰과 연결이 끊깁니다.")
    flow = registration.RegistrationFlow(store, state_store.FileStateStore(state_store.default_path()), revoke=args.revoke)
    if registration.show_window(flow):
        flow.confirm()
        print("등록을 확정했습니다. 새 키로 보낸 첫 메시지를 휴대폰이 받으면 휴대폰 쪽 교체도 확정됩니다.")
    else:
        flow.cancel()
        if existing and not args.revoke:
            print("등록을 취소했습니다. 기존 키를 계속 사용합니다.")
        else:
            print("등록을 취소했습니다. 저장된 키가 없습니다.")


def cmd_import_sa(args) -> None:
    source = Path(args.path)
    raw = source.read_bytes()
    try:
        info = validate_service_account(raw)
    except ValueError as e:
        sys.exit(f"가져오기 실패: {e}")
    if "firebase-adminsdk" in info["client_email"]:
        print("경고: Firebase Admin SDK 기본 계정은 권한이 넓습니다. FCM 발송 역할만 가진 전용 계정을 권장합니다.")
    target = default_sa_path()
    DpapiServiceAccountStore(target).save(raw)
    print(f"서비스 계정({info['client_email']})을 DPAPI로 암호화하여 저장했습니다: {target}")
    print(f"원본 JSON 파일은 더 이상 필요 없으므로 직접 삭제하세요: {source.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="gmb")
    sub = parser.add_subparsers(dest="command", required=True)
    reg = sub.add_parser("register", help="휴대폰 기기 등록 (QR 표시)")
    reg.add_argument("--revoke", action="store_true", help="유출 대응: 기존 키와 토픽을 즉시 삭제한 뒤 등록")
    reg.set_defaults(func=cmd_register)
    sa = sub.add_parser("import-sa", help="서비스 계정 JSON을 암호화하여 저장")
    sa.add_argument("path")
    sa.set_defaults(func=cmd_import_sa)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
