import pytest

from core.models import DealInput, MarketOffer, Product, Decision
from core.profit_engine import ProfitEngine


def make_deal(amazon_price=50.0, ebay_price=100.0, fee=10.0):
    product = Product(title="Test product", brand="Test")
    return DealInput(
        product=product,
        amazon=MarketOffer("amazon", "https://amazon.example/test", amazon_price),
        ebay=MarketOffer("ebay", "https://ebay.example/test", ebay_price),
        ebay_fee_percent=fee,
        packaging_cost=2.0,
    )


def test_profitable_deal():
    result = ProfitEngine.calculate(make_deal())
    assert result.profit == 38.0
    assert result.roi == 76.0
    assert result.decision is Decision.BUY
    assert result.score > 0


def test_low_profit_is_ignored():
    result = ProfitEngine.calculate(make_deal(amazon_price=90, ebay_price=100))
    assert result.decision is Decision.IGNORE
    assert "Gewinn" in result.reason


def test_zero_amazon_price_is_rejected():
    with pytest.raises(ValueError):
        ProfitEngine.calculate(make_deal(amazon_price=0))
