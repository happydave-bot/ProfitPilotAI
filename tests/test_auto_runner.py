from core.auto_runner import AutoRunner, RunnerConfig
from core.deal_scanner import ScanCandidate
from core.models import DealResult, Decision, MarketOffer, Product
from core.notifiers import MemoryNotifier


def candidate():
    product = Product(title="Bosch Akkuschrauber", brand="Bosch", ean="123")
    amazon = MarketOffer(source="amazon", url="https://amazon.example", price=40.0)
    ebay = MarketOffer(source="ebay", url="https://ebay.example", price=85.0)
    deal = DealResult(profit=30.0, roi=60.0, score=90, decision=Decision.BUY, reason="Profitabler Deal")
    return ScanCandidate(product, amazon, ebay, 100.0, deal)


def test_runner_starts_when_state_load_fails():
    class BrokenStateStore:
        def load(self):
            raise OSError("state file unreadable")

        def save(self, seen):
            raise AssertionError("save should not be reached")

    notifier = MemoryNotifier()
    runner = AutoRunner(
        lambda: [candidate()],
        notifier,
        sleep=lambda _: None,
        state_store=BrokenStateStore(),
    )

    assert len(runner.run_once()) == 1
    assert len(notifier.messages) == 1


def test_runner_can_scan_after_transient_state_load_failure():
    class FlakyStateStore:
        def load(self):
            raise ValueError("invalid state")

        def save(self, seen):
            raise AssertionError("save should not be reached")

    runner = AutoRunner(
        lambda: [candidate()],
        MemoryNotifier(),
        sleep=lambda _: None,
        state_store=FlakyStateStore(),
    )

    assert runner.run(max_cycles=1) == 1


def test_runner_alerts_once_across_cycles():
    notifier = MemoryNotifier()
    runner = AutoRunner(lambda: [candidate()], notifier, sleep=lambda _: None)
    assert len(runner.run_once()) == 1
    assert len(runner.run_once()) == 0
    assert len(notifier.messages) == 1


def test_runner_returns_no_alerts_when_scan_fails():
    calls = 0

    def broken_scan():
        nonlocal calls
        calls += 1
        raise RuntimeError("scan failed")

    runner = AutoRunner(broken_scan, MemoryNotifier(), sleep=lambda _: None)

    assert runner.run_once() == []
    assert calls == 1


def test_runner_continues_after_scan_failure():
    calls = 0

    def flaky_scan():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary failure")
        return [candidate()]

    notifier = MemoryNotifier()
    runner = AutoRunner(flaky_scan, notifier, sleep=lambda _: None)

    assert runner.run(max_cycles=2) == 2
    assert len(notifier.messages) == 1


def test_runner_continues_when_notifier_fails():
    class BrokenNotifier:
        def send(self, message):
            raise RuntimeError("network")

    runner = AutoRunner(lambda: [candidate()], BrokenNotifier(), sleep=lambda _: None)
    assert runner.run(max_cycles=2) == 2


def test_runner_retries_failed_notification_on_next_cycle():
    class BrokenOnceNotifier:
        def __init__(self):
            self.calls = 0

        def send(self, message):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("network")

    notifier = BrokenOnceNotifier()
    runner = AutoRunner(lambda: [candidate()], notifier, sleep=lambda _: None)

    assert len(runner.run_once()) == 1
    assert len(runner.run_once()) == 1
    assert notifier.calls == 2


def test_runner_does_not_persist_failed_notification(tmp_path):
    from core.state_store import JsonStateStore

    class BrokenNotifier:
        def send(self, message):
            raise RuntimeError("network")

    store = JsonStateStore(tmp_path / "state.json")
    runner = AutoRunner(lambda: [candidate()], BrokenNotifier(), sleep=lambda _: None, state_store=store)

    assert len(runner.run_once()) == 1
    assert store.load() == set()


def test_runner_continues_when_state_save_fails():
    class BrokenStateStore:
        def load(self):
            return set()

        def save(self, seen):
            raise OSError("disk full")

    notifier = MemoryNotifier()
    runner = AutoRunner(
        lambda: [candidate()],
        notifier,
        sleep=lambda _: None,
        state_store=BrokenStateStore(),
    )

    assert len(runner.run_once()) == 1
    assert len(notifier.messages) == 1


def test_runner_can_continue_after_transient_state_save_failure():
    class FlakyStateStore:
        def __init__(self):
            self.calls = 0

        def load(self):
            return set()

        def save(self, seen):
            self.calls += 1
            if self.calls == 1:
                raise OSError("temporary disk failure")

    store = FlakyStateStore()
    runner = AutoRunner(
        lambda: [candidate()],
        MemoryNotifier(),
        sleep=lambda _: None,
        state_store=store,
    )

    assert len(runner.run_once()) == 1
    assert len(runner.run_once()) == 0
    assert store.calls == 1


def test_runner_rejects_invalid_interval():
    try:
        AutoRunner(lambda: [], MemoryNotifier(), config=RunnerConfig(interval_seconds=0))
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "größer als 0" in str(exc)


def test_runner_rejects_non_finite_interval():
    for value in (float("inf"), float("-inf"), float("nan")):
        try:
            AutoRunner(lambda: [], MemoryNotifier(), config=RunnerConfig(interval_seconds=value))
            assert False, "expected ValueError"
        except ValueError as exc:
            assert "endlich" in str(exc)
