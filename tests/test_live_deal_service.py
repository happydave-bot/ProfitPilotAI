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
