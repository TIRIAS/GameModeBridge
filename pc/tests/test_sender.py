import json

import pytest

from gmb import sender


class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


class FakeSession:
    """응답 목록을 차례로 돌려줌. 예외 인스턴스는 발생시킴."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, json=None, timeout=None):
        self.calls.append((url, json, timeout))
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return FakeResponse(r)


SA = {"project_id": "gamemodebridge"}
ENV = {"v": "1", "iv": "aaaa", "ct": "bbbb"}


def make(responses):
    sleeps = []
    session = FakeSession(responses)
    return sender.FcmSender(SA, session=session, sleep=sleeps.append), session, sleeps


def test_fcm_message_options():
    msg = sender.build_fcm_message("gmb_x", ENV)["message"]
    assert msg["topic"] == "gmb_x"
    assert msg["data"] == ENV
    assert msg["android"] == {"priority": "HIGH", "ttl": "60s"}  # collapse_key 없음
    assert "notification" not in msg  # 데이터 메시지만 사용


def test_send_success_first_try():
    s, session, sleeps = make([200])
    s.send("gmb_x", ENV)
    assert len(session.calls) == 1
    url, body, timeout = session.calls[0]
    assert url == "https://fcm.googleapis.com/v1/projects/gamemodebridge/messages:send"
    assert timeout == sender.REQUEST_TIMEOUT_SEC
    assert sleeps == []


def test_retries_with_same_envelope_then_succeeds():
    s, session, sleeps = make([500, ConnectionError("x"), 200])
    s.send("gmb_x", ENV)
    bodies = [c[1] for c in session.calls]
    assert len(bodies) == 3 and all(b == bodies[0] for b in bodies)
    assert sleeps == [1, 2]


def test_gives_up_after_three_retries():
    s, session, sleeps = make([503, 503, 503, 503])
    with pytest.raises(sender.SendError):
        s.send("gmb_x", ENV)
    assert len(session.calls) == 4
    assert sleeps == [1, 2, 2]


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_permanent_error_is_not_retried(status):
    s, session, sleeps = make([status])
    with pytest.raises(sender.SendError):
        s.send("gmb_x", ENV)
    assert len(session.calls) == 1


def test_dry_run_writes_file(tmp_path):
    path = tmp_path / "dry.log"
    sender.DryRunSender(path).send("gmb_x", ENV)
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["fcm"] == sender.build_fcm_message("gmb_x", ENV)
