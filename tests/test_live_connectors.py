from connectors.amazon import AmazonConnector
from connectors.ebay import EbayConnector
from connectors.market_data import MarketListing
from core.models import MarketOffer, Product


def listing(source: str) -> MarketListing:
    product = Product(title="Bosch GSR 18V", brand="Bosch", ean="123")
    offer = MarketOffer(source=source, url="https://example.test/item", price=100.0)
    return MarketListing(product=product, offer=offer)


def test_unconfigured_connector_reports_status_and_fails_cleanly():
    connector = AmazonConnector()
    assert not connector.status.configured
    try:
        connector.search("Bosch")
    except RuntimeError as exc:
        assert "nicht konfiguriert" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")


def test_configured_amazon_connector_normalizes_fetcher_result():
    connector = AmazonConnector(lambda query: [listing("amazon")])
    assert connector.status.configured
    assert connector.search("Bosch")[0].offer.source == "amazon"


def test_configured_ebay_connector_normalizes_fetcher_result():
    connector = EbayConnector(lambda query: [listing("ebay")])
    assert connector.status.configured
    assert connector.search("Bosch")[0].offer.source == "ebay"
