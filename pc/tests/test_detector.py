import pytest

from gmb.detector import Bridge, Detector
from gmb.providers import FakeProvider
from gmb.sender import SendError

A, B = "game_a.exe", "game_b.exe"


# ---------- Detector: 감지 규칙 ----------

def run(detector, steps, start=0.0, step=2.0):
    return [detector.update(s, start + i * step)[0] for i, s in enumerate(steps)]


def test_game_start_is_immediate():
    assert run(Detector((A,)), [set(), {A}]) == ["off", "on"]


def test_case_insensitive_match_and_display_name():
    d = Detector(("Game_A.EXE",))
    assert d.update({"game_a.exe"}, 0) == ("on", "Game_A")


def test_off_only_after_grace_period():
    d = Detector((A,), grace_sec=4)
    assert d.update({A}, 0)[0] == "on"
    assert d.update(set(), 2)[0] == "on"   # 종료 감지 시작
    assert d.update(set(), 4)[0] == "on"   # 2초 경과
    assert d.update(set(), 6)[0] == "off"  # 4초 경과


def test_restart_within_grace_keeps_on():
    assert run(Detector((A,)), [{A}, set(), {A}, set(), {A}]) == ["on"] * 5


def test_switch_to_other_game_within_grace_keeps_on():
    d = Detector((A, B))
    assert run(d, [{A}, set(), {B}]) == ["on", "on", "on"]
    assert d.game == "game_b"


def test_multiple_games_off_only_when_last_ends():
    states = run(Detector((A, B)), [{A}, {A, B}, {B}, set(), set(), set()])
    assert states == ["on", "on", "on", "on", "on", "off"]


def test_query_failure_keeps_previous_state():
    d = Detector((A,))
    d.update({A}, 0)
    assert run(d, [None, None, None, None], start=2) == ["on"] * 4
    d2 = Detector((A,))
    assert d2.update(None, 0)[0] == "off"


def test_unrelated_processes_ignored():
    assert run(Detector((A,)), [{"explorer.exe", "steam.exe"}]) == ["off"]


def test_set_games_adds_new_game_immediately():
    d = Detector(())
    assert d.update({A}, 0)[0] == "off"
    d.set_games((A,))
    assert d.update({A}, 2)[0] == "on"


def test_set_games_removing_running_game_ends_after_grace():
    d = Detector((A,))
    d.update({A}, 0)
    d.set_games(())
    assert [d.update({A}, t)[0] for t in (2, 4, 6)] == ["on", "on", "off"]


# ---------- Bridge: 상태 동기화 규칙 ----------

class Recorder:
    def __init__(self):
        self.sent = []
        self.fail = False

    def __call__(self, state, game):
        if self.fail:
            raise SendError("HTTP 503")
        self.sent.append((state, game))


def make(steps, **kw):
    rec = Recorder()
    return Bridge(FakeProvider(steps), Detector((A, B)), rec, **kw), rec


def tick_all(bridge, n, start=0.0, step=2.0):
    for i in range(n):
        bridge.tick(start + i * step)


def test_app_start_sends_current_off():
    bridge, rec = make([set()])
    tick_all(bridge, 3)
    assert rec.sent == [("off", "")]


def test_app_start_while_game_running_sends_on_immediately():
    bridge, rec = make([{A}])
    bridge.tick(0)
    assert rec.sent == [("on", "game_a")]


def test_no_duplicate_sends_for_same_state():
    bridge, rec = make([set(), {A}, {A}, {A}, {A, B}, {B}])
    tick_all(bridge, 6)
    assert [s for s, _ in rec.sent] == ["off", "on"]


def test_off_sent_once_after_grace():
    bridge, rec = make([{A}, set(), set(), set(), set()])
    tick_all(bridge, 5)
    assert rec.sent == [("on", "game_a"), ("off", "game_a")]


def test_send_failure_retries_every_30s_with_current_state():
    bridge, rec = make([{A}] + [{A}] * 30)
    rec.fail = True
    bridge.tick(0)
    assert bridge.unsent and "발송 실패" in bridge.status
    rec.fail = False
    for t in range(2, 30, 2):  # 30초 전에는 다시 보내지 않음
        bridge.tick(t)
    assert rec.sent == []
    bridge.tick(30)
    assert rec.sent == [("on", "game_a")]
    assert not bridge.unsent and "FCM 접수 완료" in bridge.status


def test_state_change_during_failure_sends_only_latest():
    # on 발송 실패 후 게임 종료: 실패한 on을 다시 보내지 않고 최신 off만 보냄
    bridge, rec = make([{A}, set(), set(), set(), set()])
    rec.fail = True
    bridge.tick(0)
    rec.fail = False
    tick_all(bridge, 4, start=2)
    assert rec.sent == [("off", "game_a")]


def test_resume_from_sleep_resends_current_state():
    bridge, rec = make([{A}] * 5)
    bridge.tick(0)
    bridge.tick(2)
    bridge.tick(2 + 600)  # 10분 동안 감지 주기가 멈춤 = 절전 해제
    assert rec.sent == [("on", "game_a"), ("on", "game_a")]


def test_resend_current_on_request():
    bridge, rec = make([set()] * 5)
    bridge.tick(0)
    bridge.resend_current()
    bridge.tick(2)
    bridge.tick(4)
    assert rec.sent == [("off", ""), ("off", "")]


def test_pause_while_playing_sends_off_and_stops_detection():
    bridge, rec = make([{A}] * 10)
    bridge.tick(0)
    bridge.pause(2)
    tick_all(bridge, 3, start=4)
    assert rec.sent == [("on", "game_a"), ("off", "game_a")]
    bridge.resume()
    bridge.tick(10)
    assert rec.sent[-1] == ("on", "game_a")


def test_pause_while_idle_sends_nothing():
    bridge, rec = make([set()] * 3)
    bridge.tick(0)
    bridge.pause(2)
    assert rec.sent == [("off", "")]


@pytest.mark.parametrize("steps,expected", [([{A}], [("on", "game_a"), ("off", "game_a")]), ([set()], [("off", "")])])
def test_shutdown_sends_off_only_if_playing(steps, expected):
    bridge, rec = make(steps)
    bridge.tick(0)
    bridge.shutdown(2)
    assert rec.sent == expected
