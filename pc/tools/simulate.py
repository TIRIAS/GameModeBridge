"""메시지 시나리오 시뮬레이터 (CLAUDE.md 7장).

실행: pc 폴더에서 .venv\\Scripts\\python.exe -m tools.simulate <시나리오> [--live] [--gap 초]
기본은 드라이런이며 --live 사용 시 등록된 휴대폰으로 실제 발송함.
multi, flapping은 가짜 프로세스 목록으로 실제 감지 로직(Detector, Bridge)을 거쳐 발송함.
"""

import argparse
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from gmb import crypto, state_store
from gmb.detector import Bridge, Detector
from gmb.providers import FakeProvider
from gmb.secret_store import DpapiServiceAccountStore, KeyringSecretStore, default_sa_path
from gmb.sender import DryRunSender, FcmSender

GAME = "SIMULATOR"


@dataclass
class Context:
    key: bytes
    topic: str
    state: object
    sender: object
    now: Callable[[], int] = lambda: int(time.time())
    sleep: Callable[[float], None] = time.sleep
    gap: float = 5.0
    log: list = field(default_factory=list)

    def envelope(self, state: str, ts: int | None = None) -> dict:
        payload = crypto.make_payload(state, GAME, self.state.next_seq(), self.now() if ts is None else ts)
        return crypto.seal(self.key, payload)

    def send(self, label: str, envelope: dict, expected: str) -> None:
        self.sender.send(self.topic, envelope)
        line = f"{time.strftime('%H:%M:%S')} 발송: {label} → 휴대폰 기대 결과: {expected}"
        self.log.append(line)
        print(line)


def _tamper(envelope: dict) -> dict:
    raw = bytearray(crypto.b64url_decode(envelope["ct"]))
    raw[0] ^= 0x01
    return dict(envelope, ct=crypto.b64url_encode(bytes(raw)))


def basic(ctx: Context) -> None:
    ctx.send("켜기", ctx.envelope("on"), "GAMEMODE_ON 알림")
    ctx.sleep(ctx.gap)
    ctx.send("끄기", ctx.envelope("off"), "GAMEMODE_OFF 알림")


def stale(ctx: Context) -> None:
    ctx.send("5분 전 시각의 켜기", ctx.envelope("on", ts=ctx.now() - 300), "폐기: STALE")


def replay(ctx: Context) -> None:
    env = ctx.envelope("off")
    ctx.send("끄기", env, "GAMEMODE_OFF 알림")
    ctx.sleep(ctx.gap)
    ctx.send("같은 끄기 다시 발송", env, "폐기: SEQ")


def reorder(ctx: Context) -> None:
    on = ctx.envelope("on")
    off = ctx.envelope("off")
    ctx.send("나중에 만든 끄기 먼저", off, "GAMEMODE_OFF 알림")
    ctx.sleep(ctx.gap)
    ctx.send("먼저 만든 켜기 늦게", on, "폐기: SEQ")


def tamper(ctx: Context) -> None:
    ctx.send("암호문 1바이트 변조한 켜기", _tamper(ctx.envelope("on")), "폐기: AUTH")


POLL_SEC = 2


def _run_detection(ctx: Context, steps: list[set[str]], expected: dict[int, str]) -> None:
    """steps를 감지 주기(2초)마다 재생함. expected는 해당 순서의 발송에 대한 휴대폰 기대 결과."""
    count = {"n": 0}

    def send_state(state: str, game: str) -> None:
        count["n"] += 1
        payload = crypto.make_payload(state, game, ctx.state.next_seq(), ctx.now())
        ctx.send(f"감지 결과 {state} ({game})", crypto.seal(ctx.key, payload), expected.get(count["n"], "예상하지 않은 발송"))

    bridge = Bridge(FakeProvider(steps), Detector(("game_a.exe", "game_b.exe")), send_state)
    start = ctx.now()
    for i in range(len(steps)):
        bridge.tick(start + i * POLL_SEC)
        ctx.sleep(POLL_SEC)
    bridge.shutdown(start + len(steps) * POLL_SEC)


def multi(ctx: Context) -> None:
    # 게임 A 실행, B 추가 실행, A 종료, B 종료. 마지막 게임 종료 후 유예 4초가 지나야 off 1회
    a, b = "game_a.exe", "game_b.exe"
    _run_detection(ctx, [set(), {a}, {a, b}, {a, b}, {b}, {b}, set(), set(), set(), set()],
                   {1: "GAMEMODE_OFF 알림 (시작 시 현재 상태)", 2: "GAMEMODE_ON 알림", 3: "GAMEMODE_OFF 알림"})


def flapping(ctx: Context) -> None:
    # 2초 간격으로 꺼졌다 켜짐을 반복. 유예 4초보다 짧으므로 on 1회 후 마지막에만 off
    a = "game_a.exe"
    _run_detection(ctx, [set(), {a}, set(), {a}, set(), {a}, set(), set(), set(), set()],
                   {1: "GAMEMODE_OFF 알림 (시작 시 현재 상태)", 2: "GAMEMODE_ON 알림", 3: "GAMEMODE_OFF 알림"})


SCENARIOS = {"basic": basic, "stale": stale, "replay": replay, "reorder": reorder, "tamper": tamper,
             "multi": multi, "flapping": flapping}


def main() -> None:
    parser = argparse.ArgumentParser(prog="simulate")
    parser.add_argument("scenario", choices=SCENARIOS)
    parser.add_argument("--live", action="store_true", help="등록된 휴대폰으로 실제 FCM 발송")
    parser.add_argument("--gap", type=float, default=5.0, help="메시지 사이 간격(초)")
    args = parser.parse_args()

    creds = KeyringSecretStore().load()
    if creds is None:
        raise SystemExit("등록된 키가 없습니다. 먼저 python -m gmb register 를 실행하세요.")
    if args.live:
        sender = FcmSender(DpapiServiceAccountStore(default_sa_path()).load())
    else:
        sender = DryRunSender(Path(os.environ["APPDATA"]) / "GameModeBridge" / "dryrun.log")
    ctx = Context(creds.key, creds.topic, state_store.FileStateStore(state_store.default_path()), sender, gap=args.gap)
    print(f"시나리오 {args.scenario} ({'실제 발송' if args.live else '드라이런'})")
    SCENARIOS[args.scenario](ctx)


if __name__ == "__main__":
    main()
