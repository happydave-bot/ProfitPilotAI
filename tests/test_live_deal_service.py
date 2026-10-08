import logging
import math

import pytest

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


def test_profitable_cross_market_deal():
    service = LiveDealService(FakeAmazon(), FakeEbay())
    results = service.scan("Bosch Akkuschrauber")
    assert len(results) == 1
    assert results[0].deal.profit > 0
    assert results[0].match_confidence == 100.0


def test_empty_query_returns_no_results():
    service = LiveDealService(FakeAmazon(), FakeEbay())
    assert service.scan("   ") == []


class RecordingEbay:
    def __init__(self, listings_by_query):
        self.listings_by_query = listings_by_query
        self.queries = []

    def search(self, query):
        self.queries.append(query)
        return list(self.listings_by_query.get(query, []))


def test_prefers_ean_before_title():
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


def test_falls_back_to_title_when_identifier_finds_no_deal():
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


def test_includes_ebay_shipping_in_real_profit():
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
    assert results[0].deal.profit == 20.29


def test_applies_ebay_competition_killer_end_to_end():
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


def test_ebay_query_error_falls_back_to_next_query_and_logs(caplog):
    product = Product(title="Bosch Akkuschrauber 18V", brand="Bosch", ean="123")
    matched = Product(title="Bosch Akkuschrauber 18V", brand="Bosch", ean="123")

    class FlakyEbay:
        def __init__(self):
            self.queries = []

        def search(self, query):
            self.queries.append(query)
            if query == "123":
                raise RuntimeError("temporary eBay outage")
            return [MarketListing(
                matched,
                MarketOffer("ebay", "https://ebay.example/p", 85.0),
            )]

    service = LiveDealService(FakeAmazon(), FlakyEbay())

    with caplog.at_level(logging.ERROR):
        results = service.scan("Bosch Akkuschrauber")

    assert len(results) == 1
    assert service.ebay.queries == ["123", "Bosch Akkuschrauber 18V"]
    assert "eBay-Suche fehlgeschlagen" in caplog.text


def test_ebay_query_errors_do_not_crash_scan_when_all_queries_fail(caplog):
    class BrokenEbay:
        def search(self, query):
            raise RuntimeError("eBay unavailable")

    service = LiveDealService(FakeAmazon(), BrokenEbay())

    with caplog.at_level(logging.ERROR):
        results = service.scan("Bosch Akkuschrauber")

    assert results == []
    assert caplog.text.count("eBay-Suche fehlgeschlagen") == 1


def test_live_deal_config_accepts_valid_values():
    config = LiveDealConfig(ebay_fee_percent=12.9, packaging_cost=2.0, max_ebay_results=20)

    assert config.ebay_fee_percent == 12.9
    assert config.packaging_cost == 2.0
    assert config.max_ebay_results == 20


@pytest.mark.parametrize("value", [-0.01, 100.01, math.inf, -math.inf, math.nan])
def test_live_deal_config_rejects_invalid_ebay_fee(value):
    with pytest.raises(ValueError, match="eBay fee percent"):
        LiveDealConfig(ebay_fee_percent=value)


@pytest.mark.parametrize("value", [-0.01, math.inf, -math.inf, math.nan])
def test_live_deal_config_rejects_invalid_packaging_cost(value):
    with pytest.raises(ValueError, match="Packaging cost"):
        LiveDealConfig(packaging_cost=value)


@pytest.mark.parametrize("value", [0, -1])
def test_live_deal_config_rejects_invalid_max_ebay_results(value):
    with pytest.raises(ValueError, match="Maximum eBay results"):
        LiveDealConfig(max_ebay_results=value)
