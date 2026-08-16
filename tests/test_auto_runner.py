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


def test_runner_alerts_once_across_cycles():
    notifier = MemoryNotifier()
    runner = AutoRunner(lambda: [candidate()], notifier, sleep=lambda _: None)
    assert len(runner.run_once()) == 1
    assert len(runner.run_once()) == 0
    assert len(notifier.messages) == 1


def test_runner_continues_when_notifier_fails():
    class BrokenNotifier:
        def send(self, message):
            raise RuntimeError("network")

    runner = AutoRunner(lambda: [candidate()], BrokenNotifier(), sleep=lambda _: None)
    assert len(runner.run(max_cycles=2)) == 2


def test_runner_rejects_invalid_interval():
    try:
        AutoRunner(lambda: [], MemoryNotifier(), config=RunnerConfig(interval_seconds=0))
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "größer als 0" in str(exc)
