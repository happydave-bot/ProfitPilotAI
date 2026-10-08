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
    assert result.profit == 37.55
    assert result.roi == 75.1
    assert result.decision is Decision.BUY
    assert result.score > 0


def test_low_profit_is_ignored():
    result = ProfitEngine.calculate(make_deal(amazon_price=90, ebay_price=100))
    assert result.decision is Decision.IGNORE
    assert "Gewinn" in result.reason


def test_zero_amazon_price_is_rejected():
    with pytest.raises(ValueError):
        ProfitEngine.calculate(make_deal(amazon_price=0))


def test_ebay_fee_includes_shipping_and_fixed_order_fee():
    deal = make_deal(amazon_price=40.0, ebay_price=85.0, fee=12.9)
    deal = DealInput(
        product=deal.product,
        amazon=deal.amazon,
        ebay=MarketOffer(
            "ebay",
            "https://ebay.example/test",
            85.0,
            shipping=10.0,
        ),
        ebay_fee_percent=deal.ebay_fee_percent,
        packaging_cost=deal.packaging_cost,
    )

    result = ProfitEngine.calculate(deal)

    assert result.profit == 20.29


def test_ebay_fixed_order_fee_is_035_at_or_below_10_euros():
    deal = make_deal(amazon_price=5.0, ebay_price=10.0, fee=0.0)

    result = ProfitEngine.calculate(deal)

    assert result.profit == 2.65


def test_ebay_fixed_order_fee_is_045_above_10_euros():
    deal = make_deal(amazon_price=5.0, ebay_price=10.01, fee=0.0)

    result = ProfitEngine.calculate(deal)

    assert result.profit == 2.56
