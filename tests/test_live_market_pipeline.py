from connectors.market_data import MarketListing
from core.live_market_pipeline import LiveMarketPipeline
from core.models import MarketOffer, Product


class FakeConnector:
    def __init__(self, listings):
        self.listings = listings
        self.queries = []

    def search(self, query):
        self.queries.append(query)
        return list(self.listings)


def test_live_pipeline_bridges_amazon_to_ebay_and_scanner():
    product = Product(title="Bosch Akkuschrauber", brand="Bosch", ean="123")
    amazon_offer = MarketOffer(source="amazon", url="https://amazon.example", price=40.0)
    ebay_offer = MarketOffer(source="ebay", url="https://ebay.example", price=85.0)
    amazon = FakeConnector([MarketListing(product, amazon_offer)])
    ebay = FakeConnector([MarketListing(product, ebay_offer)])

    results = LiveMarketPipeline(amazon, ebay).scan("Bosch Akkuschrauber")

    assert len(results) == 1
    assert results[0].deals[0].deal.profit > 0
    assert ebay.queries == ["Bosch Akkuschrauber"]


def test_live_pipeline_ignores_unmatched_ebay_product():
    amazon_product = Product(title="Bosch Akkuschrauber", brand="Bosch", ean="123")
    ebay_product = Product(title="Makita Bohrmaschine", brand="Makita", ean="999")
    amazon = FakeConnector([MarketListing(amazon_product, MarketOffer("amazon", "https://a", 40.0))])
    ebay = FakeConnector([MarketListing(ebay_product, MarketOffer("ebay", "https://e", 85.0))])

    results = LiveMarketPipeline(amazon, ebay).scan("Bosch Akkuschrauber")

    assert results == []
