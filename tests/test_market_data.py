from connectors.market_data import InMemoryConnector, MarketListing
from core.models import MarketOffer, Product


def test_connector_finds_product_by_title():
    listing = MarketListing(
        Product(title="Bosch GSR 18V Akkuschrauber", brand="Bosch", ean="123"),
        MarketOffer(source="ebay", url="https://example.test/1", price=89.0),
    )
    connector = InMemoryConnector([listing])
    results = connector.search("GSR 18V")
    assert results == [listing]


def test_connector_finds_product_by_ean():
    listing = MarketListing(
        Product(title="Bosch GSR 18V", brand="Bosch", ean="1234567890123"),
        MarketOffer(source="amazon", url="https://example.test/2", price=99.0),
    )
    connector = InMemoryConnector([listing])
    assert connector.search("1234567890123") == [listing]


def test_connector_empty_query_returns_all():
    listings = [
        MarketListing(Product(title="A", brand="X"), MarketOffer(source="x", url="u", price=1)),
        MarketListing(Product(title="B", brand="Y"), MarketOffer(source="x", url="v", price=2)),
    ]
    assert len(InMemoryConnector(listings).search("")) == 2
