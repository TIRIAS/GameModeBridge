import psutil
import pytest

from gmb.providers import FakeProvider, ProcessQueryError, PsutilProvider


class P:
    def __init__(self, name):
        self.info = {"name": name}


def test_psutil_provider_lowercases_and_skips_missing_names(monkeypatch):
    monkeypatch.setattr(psutil, "process_iter", lambda attrs: iter([P("Game.EXE"), P(None), P("explorer.exe")]))
    assert PsutilProvider().running_names() == {"game.exe", "explorer.exe"}


def test_psutil_query_failure_is_distinct_from_empty(monkeypatch):
    def boom(attrs):
        raise psutil.Error("x")
    monkeypatch.setattr(psutil, "process_iter", boom)
    with pytest.raises(ProcessQueryError):
        PsutilProvider().running_names()


def test_psutil_real_call_works():
    # 실제 시스템에서 최소한 현재 파이썬 프로세스는 보여야 함
    assert any(n.startswith("python") for n in PsutilProvider().running_names())


def test_fake_provider_replays_and_repeats_last():
    p = FakeProvider([{"A.exe"}, None, set()])
    assert p.running_names() == {"a.exe"}
    with pytest.raises(ProcessQueryError):
        p.running_names()
    assert p.running_names() == set()
    assert p.running_names() == set()


def test_running_exe_names_keeps_case_and_dedupes(mocker):
    from gmb.providers import running_exe_names

    procs = [mocker.Mock(info={"name": n}) for n in ["Game.exe", "game.EXE", "explorer.exe", "System", None]]
    mocker.patch("gmb.providers.psutil.process_iter", return_value=procs)
    assert running_exe_names() == ["explorer.exe", "Game.exe"]


def test_running_exe_names_returns_empty_on_failure(mocker):
    from gmb.providers import running_exe_names

    mocker.patch("gmb.providers.psutil.process_iter", side_effect=psutil.Error())
    assert running_exe_names() == []
