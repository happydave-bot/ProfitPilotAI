from core.deal_killer import DealKillerEngine
from core.models import DealResult, Decision, MarketOffer


def base_result(profit=25.0):
    return DealResult(profit=profit, roi=50.0, score=90, decision=Decision.BUY, reason="")


def offer(source, **kwargs):
    return MarketOffer(source=source, url="https://example.com", price=50.0, **kwargs)


def test_rejects_amazon_self_sold():
    result = DealKillerEngine.evaluate(base_result(), offer("amazon", seller="Amazon"), offer("ebay"))
    assert result.decision is Decision.IGNORE
    assert "selbst" in result.reason


def test_rejects_oversupplied_ebay_market():
    result = DealKillerEngine.evaluate(base_result(), offer("amazon"), offer("ebay", competition_count=26))
    assert result.decision is Decision.IGNORE


def test_rejects_bad_profit_and_risk_signals():
    result = DealKillerEngine.evaluate(
        base_result(profit=9.99),
        offer("amazon"),
        offer("ebay", price_trend_percent=-10.0, demand_score=20.0, return_rate_percent=20.0),
    )
    assert result.decision is Decision.IGNORE
    assert result.reason == "Gewinn unter Mindestziel"


def test_allows_clean_deal():
    result = DealKillerEngine.evaluate(
        base_result(),
        offer("amazon", seller="Third Party"),
        offer("ebay", competition_count=5, price_trend_percent=2.0, demand_score=80.0, return_rate_percent=4.0),
    )
    assert result.decision is Decision.BUY
