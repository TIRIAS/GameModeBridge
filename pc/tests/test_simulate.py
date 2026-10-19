import secrets

import pytest
from cryptography.exceptions import InvalidTag

from gmb import crypto
from gmb.sender import MemorySender
from gmb.state_store import FileStateStore
from tools import simulate

NOW = 1_760_000_000


@pytest.fixture
def ctx(tmp_path):
    return simulate.Context(
        key=secrets.token_bytes(32),
        topic="gmb_" + "a" * 16,
        state=FileStateStore(tmp_path / "state.json"),
        sender=MemorySender(),
        now=lambda: NOW,
        sleep=lambda s: None,
    )


def opened(ctx):
    return [crypto.open_envelope(ctx.key, env) for _, env in ctx.sender.sent]


def test_basic_sends_on_then_off_with_increasing_seq(ctx):
    simulate.basic(ctx)
    msgs = opened(ctx)
    assert [m["state"] for m in msgs] == ["on", "off"]
    assert [m["seq"] for m in msgs] == [1, 2]
    assert all(m["ts"] == NOW for m in msgs)
    assert all(t == ctx.topic for t, _ in ctx.sender.sent)


def test_stale_has_old_timestamp(ctx):
    simulate.stale(ctx)
    assert NOW - opened(ctx)[0]["ts"] >= 120


def test_replay_sends_identical_envelope(ctx):
    simulate.replay(ctx)
    (_, a), (_, b) = ctx.sender.sent
    assert a == b


def test_reorder_sends_newer_seq_first(ctx):
    simulate.reorder(ctx)
    first, second = opened(ctx)
    assert (first["state"], second["state"]) == ("off", "on")
    assert first["seq"] > second["seq"]


def test_tamper_cannot_be_opened(ctx):
    simulate.tamper(ctx)
    with pytest.raises(InvalidTag):
        crypto.open_envelope(ctx.key, ctx.sender.sent[0][1])


def test_seq_continues_across_scenarios(ctx):
    simulate.basic(ctx)
    simulate.basic(ctx)
    assert [m["seq"] for m in opened(ctx)] == [1, 2, 3, 4]
