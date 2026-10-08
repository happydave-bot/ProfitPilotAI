from connectors.market_data import MarketListing
from core.live_deal_service import LiveDealConfig, LiveDealService
from core.models import MarketOffer, Product


class FakeAmazon:
    def search(self, query):
        product = Product(title="Bosch Akkuschrauber 18V", brand="Bosch", ean="123")
        offer = MarketOffer(source="amazon", url="https://amazon.example/p", price=40.0)
        return [MarketListing(product, offer)]


class FakeEbay:
    def search(self, query):
        product = Product(title="Bosch Akkuschrauber 18V", brand="Bosch", ean="123")
        offer = MarketOffer(source="ebay", url="https://ebay.example/p", price=85.0)
        return [MarketListing(product, offer)]


def test_live_service_returns_profitable_cross_market_deal():
    service = LiveDealService(FakeAmazon(), FakeEbay())
    results = service.scan("Bosch Akkuschrauber")
    assert len(results) == 1
    assert results[0].deal.profit > 0
    assert results[0].match_confidence == 100.0


def test_live_service_empty_query_returns_no_results():
    service = LiveDealService(FakeAmazon(), FakeEbay())
    assert service.scan("   ") == []


class RecordingEbay:
    def __init__(self, listings_by_query):
        self.listings_by_query = listings_by_query
        self.queries = []

    def search(self, query):
        self.queries.append(query)
        return list(self.listings_by_query.get(query, []))


def test_live_service_prefers_ean_before_title():
    product = Product(title="Bosch Akkuschrauber 18V", brand="Bosch", ean="123")
    amazon = FakeAmazon()
    ebay = RecordingEbay({
        "123": [MarketListing(
            product,
            MarketOffer("ebay", "https://ebay.example/p", 85.0),
        )],
    })
    service = LiveDealService(amazon, ebay)

    results = service.scan("Bosch Akkuschrauber")

    assert len(results) == 1
    assert ebay.queries == ["123"]


def test_live_service_falls_back_to_title_when_identifier_finds_no_deal():
    product = Product(title="Bosch Akkuschrauber 18V", brand="Bosch", ean="123")
    unmatched = Product(title="Makita Bohrmaschine", brand="Makita", ean="999")
    matched = Product(title="Bosch Akkuschrauber 18V", brand="Bosch", ean="123")
    amazon = FakeAmazon()
    ebay = RecordingEbay({
        "123": [MarketListing(
            unmatched,
            MarketOffer("ebay", "https://ebay.example/unmatched", 85.0),
        )],
        "Bosch Akkuschrauber 18V": [MarketListing(
            matched,
            MarketOffer("ebay", "https://ebay.example/matched", 85.0),
        )],
    })
    service = LiveDealService(amazon, ebay)

    results = service.scan("Bosch Akkuschrauber")

    assert len(results) == 1
    assert ebay.queries == ["123", "Bosch Akkuschrauber 18V"]


def test_live_service_includes_ebay_shipping_in_real_profit():
    class ShippingEbay(FakeEbay):
        def search(self, query):
            product = Product(title="Bosch Akkuschrauber 18V", brand="Bosch", ean="123")
            offer = MarketOffer(
                source="ebay",
                url="https://ebay.example/p",
                price=85.0,
                shipping=10.0,
            )
            return [MarketListing(product, offer)]

    service = LiveDealService(FakeAmazon(), ShippingEbay())
    results = service.scan("Bosch Akkuschrauber")

    assert len(results) == 1
    assert results[0].deal.profit == 32.05


def test_live_service_applies_ebay_competition_killer_end_to_end():
    class OversuppliedEbay(FakeEbay):
        def search(self, query):
            product = Product(title="Bosch Akkuschrauber 18V", brand="Bosch", ean="123")
            offer = MarketOffer(
                source="ebay",
                url="https://ebay.example/p",
                price=85.0,
                competition_count=26,
            )
            return [MarketListing(product, offer)]

    service = LiveDealService(FakeAmazon(), OversuppliedEbay())
    assert service.scan("Bosch Akkuschrauber") == []
