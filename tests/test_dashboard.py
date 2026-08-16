from core.deal_scanner import DealScanner
from core.models import MarketOffer, Product
from ui.dashboard import deal_to_dict, render_deals


def _candidate():
    product = Product(title="Demo Product", brand="Demo", ean="4000000000000")
    amazon = MarketOffer(source="amazon", price=40.0, url="https://example.com/a")
    ebay = MarketOffer(source="ebay", price=75.0, url="https://example.com/e")
    return DealScanner.scan(
        product,
        amazon,
        [(product, ebay)],
        ebay_fee_percent=12.9,
        packaging_cost=2.0,
    )[0]


def test_dashboard_renders_ranked_deal():
    candidate = _candidate()
    output = render_deals([candidate])
    assert "Demo Product" in output
    assert "Profit" in output
    assert "ROI" in output


def test_dashboard_serializes_deal():
    data = deal_to_dict(_candidate())
    assert data["title"] == "Demo Product"
    assert data["amazon_price"] == 40.0
    assert data["ebay_price"] == 75.0
