from core.pending import PendingStore


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make():
    clock = Clock()
    return PendingStore(clock=clock), clock


def test_add_pop_roundtrip():
    store, _ = make()
    aid = store.add("restart_container", {"name": "redis"}, user_id=1)
    assert len(f"confirm:{aid}".encode()) <= 64 and len(aid) <= 20
    action = store.pop(aid, 1)
    assert (action.tool, action.args) == ("restart_container", {"name": "redis"})


def test_single_use():
    store, _ = make()
    aid = store.add("t", {}, 1)
    assert store.pop(aid, 1) is not None
    assert store.pop(aid, 1) is None


def test_expiry():
    store, clock = make()
    aid = store.add("t", {}, 1)
    clock.now += 59
    assert store.pop(aid, 1) is not None
    aid = store.add("t", {}, 1)
    clock.now += 60
    assert store.pop(aid, 1) is None


def test_other_user_does_not_consume():
    store, _ = make()
    aid = store.add("t", {}, 1)
    assert store.pop(aid, 2) is None
    assert store.pop(aid, 1) is not None


def test_unknown_id_and_unique_ids():
    store, _ = make()
    assert store.pop("nope", 1) is None
    assert len({store.add("t", {}, 1) for _ in range(50)}) == 50
