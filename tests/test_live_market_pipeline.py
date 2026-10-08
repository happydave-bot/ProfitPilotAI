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



def test_live_pipeline_accepts_ecommerce_identifiers_from_ebay_listing():
    amazon_product = Product(title="Bosch GSR 18V-65", brand="Bosch", ean="4000000000001", model="06019N0E2B")
    ebay_product = Product(title="Bosch GSR 18V-65", brand="Bosch", ean="4000000000001", model="06019N0E2B")
    amazon = FakeConnector([MarketListing(amazon_product, MarketOffer("amazon", "https://a", 40.0))])
    ebay = FakeConnector([MarketListing(ebay_product, MarketOffer("ebay", "https://e", 85.0))])

    results = LiveMarketPipeline(amazon, ebay).scan("Bosch GSR 18V-65")

    assert len(results) == 1
    assert results[0].deals[0].match_confidence == 100.0


class RecordingEbay:
    def __init__(self, listings_by_query):
        self.listings_by_query = listings_by_query
        self.queries = []

    def search(self, query):
        self.queries.append(query)
        return list(self.listings_by_query.get(query, []))


def test_live_pipeline_prefers_ean_before_model_and_title():
    product = Product(
        title="Bosch GSR 18V-65",
        brand="Bosch",
        ean="4000000000001",
        model="06019N0E2B",
    )
    amazon = FakeConnector([MarketListing(product, MarketOffer("amazon", "https://a", 40.0))])
    ebay = RecordingEbay({
        "4000000000001": [
            MarketListing(product, MarketOffer("ebay", "https://e", 85.0))
        ],
    })

    results = LiveMarketPipeline(amazon, ebay).scan("Bosch GSR 18V-65")

    assert len(results) == 1
    assert ebay.queries == ["4000000000001"]


def test_live_pipeline_falls_back_to_model_when_ean_has_no_deal():
    product = Product(
        title="Bosch GSR 18V-65",
        brand="Bosch",
        ean="4000000000001",
        model="06019N0E2B",
    )
    unmatched = Product(title="Makita Bohrmaschine", brand="Makita", ean="999")
    matched = Product(
        title="Bosch GSR 18V-65",
        brand="Bosch",
        ean="4000000000001",
        model="06019N0E2B",
    )
    amazon = FakeConnector([MarketListing(product, MarketOffer("amazon", "https://a", 40.0))])
    ebay = RecordingEbay({
        "4000000000001": [MarketListing(unmatched, MarketOffer("ebay", "https://u", 85.0))],
        "06019N0E2B": [MarketListing(matched, MarketOffer("ebay", "https://m", 85.0))],
    })

    results = LiveMarketPipeline(amazon, ebay).scan("Bosch GSR 18V-65")

    assert len(results) == 1
    assert ebay.queries == ["4000000000001", "06019N0E2B"]


def test_live_pipeline_falls_back_to_title_when_identifiers_have_no_deal():
    product = Product(
        title="Bosch GSR 18V-65",
        brand="Bosch",
        ean="4000000000001",
        model="06019N0E2B",
    )
    unmatched = Product(title="Makita Bohrmaschine", brand="Makita", ean="999")
    matched = Product(
        title="Bosch GSR 18V-65",
        brand="Bosch",
        ean="4000000000001",
        model="06019N0E2B",
    )
    amazon = FakeConnector([MarketListing(product, MarketOffer("amazon", "https://a", 40.0))])
    ebay = RecordingEbay({
        "4000000000001": [MarketListing(unmatched, MarketOffer("ebay", "https://u", 85.0))],
        "06019N0E2B": [MarketListing(unmatched, MarketOffer("ebay", "https://u2", 85.0))],
        "Bosch GSR 18V-65": [MarketListing(matched, MarketOffer("ebay", "https://t", 85.0))],
    })

    results = LiveMarketPipeline(amazon, ebay).scan("Bosch GSR 18V-65")

    assert len(results) == 1
    assert ebay.queries == ["4000000000001", "06019N0E2B", "Bosch GSR 18V-65"]
