from core.alerts import AlertConfig, DealAlertEngine, DealAlertFormatter
from core.deal_scanner import ScanCandidate
from core.models import DealResult, Decision, MarketOffer, Product


def candidate(title="Bosch Akkuschrauber", profit=30.0, roi=60.0, match=100.0, decision=Decision.BUY):
    product = Product(title=title, brand="Bosch", ean="123")
    amazon = MarketOffer(source="amazon", url="https://amazon.example", price=40.0)
    ebay = MarketOffer(source="ebay", url="https://ebay.example", price=85.0)
    deal = DealResult(profit=profit, roi=roi, score=90, decision=decision, reason="Profitabler Deal")
    return ScanCandidate(product, amazon, ebay, match, deal)


def test_alert_selects_only_strong_buy_deals():
    results = DealAlertEngine.select([
        candidate(),
        candidate("Weak", profit=8.0, roi=15.0),
        candidate("Risky", profit=50.0, roi=80.0, decision=Decision.IGNORE),
    ])
    assert len(results) == 1
    assert results[0].product.title == "Bosch Akkuschrauber"


def test_alert_respects_limit_and_ranks_by_profit():
    results = DealAlertEngine.select(
        [candidate("A", profit=25), candidate("B", profit=40), candidate("C", profit=35)],
        AlertConfig(max_alerts=2),
    )
    assert [item.product.title for item in results] == ["B", "C"]


def test_alert_formatter_contains_key_deal_numbers():
    text = DealAlertFormatter.format(candidate())
    assert "TOP DEAL" in text
    assert "Gewinn: 30.00 €" in text
    assert "ROI: 60.0 %" in text
    assert "Match: 100.0 %" in text
