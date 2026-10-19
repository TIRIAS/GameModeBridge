"""진입점.

사용:
  python -m gmb run [--config 경로] [--mode dry-run|live]
  python -m gmb list-proc [검색어]
  python -m gmb register [--revoke]
  python -m gmb import-sa <서비스 계정 JSON 경로>
"""

import argparse
import logging
import logging.handlers
import os
import sys
import time
from pathlib import Path

from gmb import config as config_mod
from gmb import registration, state_store
from gmb.detector import Bridge, Detector
from gmb.providers import ProcessQueryError, PsutilProvider
from gmb.secret_store import DpapiServiceAccountStore, KeyringSecretStore, default_sa_path, validate_service_account
from gmb.sender import DryRunSender, FcmSender, StateMessenger

DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config.json"
log = logging.getLogger("gmb")


def _setup_logging(path: Path | None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        # 로그 크기 제한과 순환 (CLAUDE.md 11장)
        handlers.append(logging.handlers.RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", handlers=handlers)


def _single_instance():
    """PC 앱 중복 실행 방지. Windows 이름 있는 뮤텍스를 프로세스가 끝날 때까지 쥐고 있음."""
    if sys.platform != "win32":
        return None
    import win32api
    import win32event
    import winerror

    handle = win32event.CreateMutex(None, False, "Local\\GameModeBridge")
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        sys.exit("GameModeBridge가 이미 실행 중입니다.")
    return handle


def cmd_run(args) -> None:
    try:
        cfg = config_mod.load(Path(args.config))
    except config_mod.ConfigError as e:
        sys.exit(f"설정 오류: {e}")
    mode = args.mode or cfg.mode
    _setup_logging(cfg.log_path)
    mutex = _single_instance()  # noqa: F841 (실행 중 유지)
    creds = KeyringSecretStore().load()
    if creds is None:
        sys.exit("등록된 키가 없습니다. 먼저 python -m gmb register 를 실행하세요.")
    if mode == "live":
        sender = FcmSender(DpapiServiceAccountStore(cfg.sa_store_path or default_sa_path()).load())
    else:
        sender = DryRunSender(Path(os.environ["APPDATA"]) / "GameModeBridge" / "dryrun.log")
    messenger = StateMessenger(creds, state_store.FileStateStore(state_store.default_path()), sender)
    bridge = Bridge(PsutilProvider(), Detector(cfg.games), messenger)
    log.info("감지 시작 (%s, 게임 %d개, %.0f초 간격)", mode, len(cfg.games), cfg.poll_interval_sec)
    # 벽시계(time.time) 사용: 절전 중에도 흐르므로 감지 주기 사이 경과 시간으로 절전 해제를 알 수 있음
    try:
        while True:
            bridge.tick(time.time())
            time.sleep(cfg.poll_interval_sec)
    except KeyboardInterrupt:
        log.info("종료 요청")
    finally:
        bridge.shutdown(time.time())


def cmd_list_proc(args) -> None:
    """실행 중인 프로세스 이름을 보여줌. 설정에 넣을 실제 게임 exe 이름 확인용 (런처와 게임 exe가 다른 경우 대비)."""
    try:
        names = PsutilProvider().running_names()
    except ProcessQueryError as e:
        sys.exit(f"프로세스 조회 실패: {e}")
    query = (args.query or "").lower()
    for name in sorted(n for n in names if query in n):
        print(name)


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
    run = sub.add_parser("run", help="게임 감지 실행")
    run.add_argument("--config", default=str(DEFAULT_CONFIG))
    run.add_argument("--mode", choices=config_mod.MODES, help="설정 파일의 mode보다 우선함")
    run.set_defaults(func=cmd_run)
    lp = sub.add_parser("list-proc", help="실행 중인 프로세스 이름 검색")
    lp.add_argument("query", nargs="?")
    lp.set_defaults(func=cmd_list_proc)
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
