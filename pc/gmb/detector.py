"""상태 전환 로직 (CLAUDE.md 5장 상태 동기화 규칙, 6단계 감지 규칙).

Detector: 실행 중인 프로세스 이름으로 대기/게임 중 상태를 판단함.
Bridge: 상태가 바뀌거나 동기화가 필요할 때만 발송함.
"""

import logging
from typing import Callable

from gmb.providers import ProcessQueryError
from gmb.sender import SendError

log = logging.getLogger(__name__)

GRACE_SEC = 4.0
RETRY_INTERVAL_SEC = 30.0
RESUME_GAP_SEC = 30.0


def display_name(exe: str) -> str:
    return exe[:-4] if exe.lower().endswith(".exe") else exe


class Detector:
    def __init__(self, games: tuple[str, ...], grace_sec: float = GRACE_SEC):
        self.set_games(games)
        self.grace_sec = grace_sec
        self.reset()

    def set_games(self, games) -> None:
        """감지 목록 변경. 게임 중 상태는 유지하며, 빠진 게임이 실행 중이면 다음 감지부터 종료로 처리함."""
        # 비교는 소문자로, 표시는 설정에 적은 표기로 함
        self.games = {g.lower(): g for g in games}

    def reset(self) -> None:
        self.playing = False
        self.game = ""
        self._ended_at: float | None = None

    def update(self, running: set[str] | None, now: float) -> tuple[str, str]:
        """(on 또는 off, 표시용 게임 이름). running이 None이면 조회 실패로 보고 이전 상태를 유지함."""
        if running is None:
            return self.state(), self.game
        found = sorted(display_name(self.games[n]) for n in self.games.keys() & running)
        if found:
            # 같은 게임 프로세스가 여러 개여도 하나라도 있으면 on 유지
            self.playing = True
            self._ended_at = None
            if self.game not in found:
                self.game = found[0]
        elif self.playing:
            # 종료 유예: 다른 게임이 곧바로 실행되면 off/on 반복을 줄임
            if self._ended_at is None:
                self._ended_at = now
            elif now - self._ended_at >= self.grace_sec:
                self.playing = False
                self._ended_at = None
        return self.state(), self.game

    def state(self) -> str:
        return "on" if self.playing else "off"


class Bridge:
    """감지 결과를 발송으로 연결함. send_state(state, game, sync)는 실패 시 SendError를 발생시킴.

    sync는 앱 시작, 감지 재개, 절전 해제 때의 자동 동기화 발송 표시임. 휴대폰은 이미 같은 off 상태면
    키워드 알림 대신 서비스 시작 알림을 띄움. 사용자가 요청한 다시 보내기와 실제 상태 변화는 sync가 아님.
    """

    def __init__(self, provider, detector: Detector, send_state: Callable[[str, str], None],
                 retry_interval: float = RETRY_INTERVAL_SEC, resume_gap: float = RESUME_GAP_SEC):
        self.provider = provider
        self.detector = detector
        self.send_state = send_state
        self.retry_interval = retry_interval
        self.resume_gap = resume_gap
        self.desired: str | None = None  # None이면 다음 감지 때 현재 상태를 발송함 (앱 시작 시)
        self.unsent = False
        self.last_attempt = 0.0
        self.last_tick: float | None = None
        self.force_sync = False  # 사용자 요청 (현재 상태 다시 보내기)
        self.auto_sync = False  # 절전 해제 감지
        self.last_sync = False  # 마지막 발송 시도가 자동 동기화였는지 (재시도 때 유지)
        self.paused = False
        self.status = "시작 중"

    def tick(self, now: float) -> None:
        if self.paused:
            return
        if self.last_tick is not None and now - self.last_tick >= self.resume_gap:
            log.info("감지 주기 사이 %.0f초 경과: 절전 해제로 보고 현재 상태를 발송함", now - self.last_tick)
            self.auto_sync = True
        self.last_tick = now
        try:
            running = self.provider.running_names()
        except ProcessQueryError as e:
            log.warning("프로세스 조회 실패, 이전 상태 유지: %s", e)
            running = None
        state, game = self.detector.update(running, now)
        was_unknown = self.desired is None
        changed = state != self.desired
        self.desired = state
        retry_due = self.unsent and now - self.last_attempt >= self.retry_interval
        if changed or self.force_sync or self.auto_sync or retry_due:
            sync = not self.force_sync and (
                was_unknown or self.auto_sync or (retry_due and not changed and self.last_sync))
            self.force_sync = False
            self.auto_sync = False
            self._send(state, game, now, sync)

    def resend_current(self) -> None:
        """트레이의 현재 상태 다시 보내기. 다음 감지 때 발송함."""
        self.force_sync = True

    def pause(self, now: float) -> None:
        """감지 일시정지. 게임 중이었다면 off를 1회 발송함."""
        self.paused = True
        if self.desired == "on":
            self._send("off", self.detector.game, now)
            self.desired = "off"
        self.status = "감지 일시정지"

    def resume(self) -> None:
        """감지 재개. 다음 감지 때 현재 상태를 발송함."""
        self.paused = False
        self.detector.reset()
        self.desired = None
        self.last_tick = None

    def shutdown(self, now: float) -> None:
        """앱 종료. 게임 중이었다면 off를 발송함."""
        if self.desired == "on":
            self._send("off", self.detector.game, now)

    def _send(self, state: str, game: str, now: float, sync: bool = False) -> None:
        self.last_attempt = now
        self.last_sync = sync
        try:
            self.send_state(state, game, sync)
        except SendError as e:
            self.unsent = True
            self.status = f"발송 실패 (재시도 중): {e}"
            log.error("발송 실패, %.0f초 후 현재 상태로 다시 시도: %s", self.retry_interval, e)
            return
        self.unsent = False
        # FCM 접수까지만 확인 가능함. 휴대폰 도착이나 모드 전환 완료를 뜻하지 않음
        label = "게임 감지됨" if state == "on" else "대기"
        self.status = f"{label} / FCM 접수 완료"
        log.info("발송: %s (%s)%s", state, game or "-", " 자동 동기화" if sync else "")
