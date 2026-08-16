from core.alert_monitor import AlertMonitor
from core.state_store import JsonStateStore


def test_state_store_round_trips_seen_fingerprints(tmp_path):
    path = tmp_path / "state.json"
    store = JsonStateStore(path)
    seen = {"abc|40.00|80.00", "def|20.00|50.00"}
    store.save(seen)
    assert store.load() == seen


def test_state_store_recovers_from_missing_or_invalid_file(tmp_path):
    store = JsonStateStore(tmp_path / "missing.json")
    assert store.load() == set()
    path = tmp_path / "broken.json"
    path.write_text("not json", encoding="utf-8")
    assert JsonStateStore(path).load() == set()


def test_runner_can_restore_monitor_state(tmp_path):
    store = JsonStateStore(tmp_path / "state.json")
    store.save({"123|40.00|85.00"})
    monitor = AlertMonitor()
    monitor.seen.update(store.load())
    assert "123|40.00|85.00" in monitor.seen
