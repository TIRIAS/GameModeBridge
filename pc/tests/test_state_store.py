from gmb.state_store import FileStateStore


def test_starts_at_zero(tmp_path):
    assert FileStateStore(tmp_path / "state.json").last_seq() == 0


def test_next_seq_increments_and_persists(tmp_path):
    path = tmp_path / "sub" / "state.json"
    store = FileStateStore(path)
    assert [store.next_seq() for _ in range(3)] == [1, 2, 3]
    # 앱 재시작: 새 인스턴스에서도 이어짐
    assert FileStateStore(path).next_seq() == 4


def test_reset(tmp_path):
    store = FileStateStore(tmp_path / "state.json")
    store.next_seq()
    store.reset()
    assert store.last_seq() == 0
    assert store.next_seq() == 1
