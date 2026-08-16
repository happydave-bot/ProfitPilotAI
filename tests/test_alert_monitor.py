from core.alert_monitor import AlertMonitor
from core.alerts import AlertConfig
from core.deal_scanner import ScanCandidate
from core.models import DealResult, Decision, MarketOffer, Product


def candidate(price=40.0):
    product = Product(title="Bosch Akkuschrauber", brand="Bosch", ean="123")
    amazon = MarketOffer(source="amazon", url="https://amazon.example", price=price)
    ebay = MarketOffer(source="ebay", url="https://ebay.example", price=85.0)
    deal = DealResult(profit=30.0, roi=60.0, score=90, decision=Decision.BUY, reason="Profitabler Deal")
    return ScanCandidate(product, amazon, ebay, 100.0, deal)


def test_monitor_emits_a_qualifying_deal_only_once():
    monitor = AlertMonitor()
    item = candidate()
    assert len(monitor.check([item])) == 1
    assert len(monitor.check([item])) == 0


def test_monitor_detects_changed_price_as_new_deal():
    monitor = AlertMonitor()
    monitor.check([candidate(40.0)])
    assert len(monitor.check([candidate(38.0)])) == 1


def test_monitor_reset_allows_alert_again():
    monitor = AlertMonitor(AlertConfig(max_alerts=1))
    item = candidate()
    monitor.check([item])
    monitor.reset()
    assert len(monitor.check([item])) == 1
