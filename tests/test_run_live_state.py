import run_live


class FakeRunner:
    class Monitor:
        seen = {"fingerprint-1"}

    monitor = Monitor()


def test_build_live_runner_does_not_eagerly_load_state(monkeypatch):
    class BrokenStateStore:
        def __init__(self, path):
            self.path = path

        def load(self):
            raise AssertionError("state load must be owned by AutoRunner")

    class FakeAutoRunner:
        def __init__(self, scan, notifier, monitor, config, state_store):
            self.state_store = state_store

    monkeypatch.setattr(run_live, "JsonStateStore", BrokenStateStore)
    monkeypatch.setattr(run_live, "AutoRunner", FakeAutoRunner)
    monkeypatch.setattr(run_live, "_read_queries", lambda: ["test"])
    monkeypatch.setattr(run_live, "TelegramNotifier", lambda: type("N", (), {"configured": True})())
    monkeypatch.setattr(run_live, "AmazonCreatorsConfig", type("A", (), {"from_env": staticmethod(lambda: None)}) )
    monkeypatch.setattr(run_live, "EbayBrowseConfig", type("E", (), {"from_env": staticmethod(lambda: object())}) )
    monkeypatch.setattr(run_live, "EbayBrowseConnector", lambda config: object())
    monkeypatch.setattr(run_live, "LiveDealService", lambda *args: object())

    runner = run_live.build_live_runner()

    assert isinstance(runner, FakeAutoRunner)


def test_persist_runner_state_swallows_save_failure(caplog, monkeypatch):
    class BrokenStateStore:
        def __init__(self, path):
            self.path = path

        def save(self, seen):
            raise OSError("disk full")

    monkeypatch.setattr(run_live, "JsonStateStore", BrokenStateStore)

    run_live.persist_runner_state(FakeRunner(), "state.json")

    assert "Alert-Status konnte beim Beenden nicht gespeichert werden" in caplog.text


def test_persist_runner_state_saves_seen_state(monkeypatch):
    saved = {}

    class StateStore:
        def __init__(self, path):
            saved["path"] = path

        def save(self, seen):
            saved["seen"] = set(seen)

    monkeypatch.setattr(run_live, "JsonStateStore", StateStore)

    run_live.persist_runner_state(FakeRunner(), "state.json")

    assert saved == {"path": "state.json", "seen": {"fingerprint-1"}}
