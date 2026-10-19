"""진입점. 사용: python -m gmb register [--revoke]"""

import argparse

from gmb import registration, state_store
from gmb.secret_store import KeyringSecretStore


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


def main() -> None:
    parser = argparse.ArgumentParser(prog="gmb")
    sub = parser.add_subparsers(dest="command", required=True)
    reg = sub.add_parser("register", help="휴대폰 기기 등록 (QR 표시)")
    reg.add_argument("--revoke", action="store_true", help="유출 대응: 기존 키와 토픽을 즉시 삭제한 뒤 등록")
    reg.set_defaults(func=cmd_register)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
