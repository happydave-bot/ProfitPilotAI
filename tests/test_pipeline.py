from connectors.market_data import InMemoryConnector, MarketListing
from core.models import MarketOffer, Product
from core.pipeline import DealPipeline


def test_pipeline_runs_end_to_end_and_ranks_deals():
    product = Product(title="Bosch GSR 18V Akkuschrauber", brand="Bosch", ean="123")
    amazon = InMemoryConnector([
        MarketListing(product, MarketOffer("amazon", "https://amazon.test/1", 100.0))
    ])
    ebay = InMemoryConnector([
        MarketListing(product, MarketOffer("ebay", "https://ebay.test/1", 160.0)),
        MarketListing(product, MarketOffer("ebay", "https://ebay.test/2", 140.0)),
    ])

    result = DealPipeline(amazon, ebay).run("Bosch GSR 18V", ebay_fee_percent=10.0)

    assert len(result.candidates) == 2
    assert result.candidates[0].ebay.price == 160.0
    assert result.candidates[0].deal.profit > result.candidates[1].deal.profit


def test_pipeline_rejects_wrong_product():
    amazon_product = Product(title="Bosch GSR 18V", brand="Bosch", ean="123")
    wrong_product = Product(title="Makita Bohrmaschine", brand="Makita", ean="999")
    amazon = InMemoryConnector([
        MarketListing(amazon_product, MarketOffer("amazon", "a", 100.0))
    ])
    ebay = InMemoryConnector([
        MarketListing(wrong_product, MarketOffer("ebay", "b", 200.0))
    ])

    result = DealPipeline(amazon, ebay).run("", ebay_fee_percent=10.0)

    assert result.candidates == ()
