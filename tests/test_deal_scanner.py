from core.deal_scanner import DealScanner
from core.models import MarketOffer, Product


def test_scanner_matches_and_ranks_profitable_offers():
    product = Product(title="Bosch GSR 18V Akkuschrauber", brand="Bosch", ean="1234567890123")
    amazon = MarketOffer(source="amazon", url="https://amazon.example/p", price=100.0)
    candidates = [
        (Product(title="Bosch GSR 18V", brand="Bosch", ean="1234567890123"), MarketOffer("ebay", "https://ebay.example/1", 160.0)),
        (Product(title="Bosch GSR 18V", brand="Bosch", ean="9999999999999"), MarketOffer("ebay", "https://ebay.example/2", 220.0)),
        (Product(title="Bosch GSR 18V Professional Akkuschrauber", brand="Bosch"), MarketOffer("ebay", "https://ebay.example/3", 150.0)),
    ]

    results = DealScanner.scan(product, amazon, candidates, ebay_fee_percent=10.0)

    assert len(results) == 2
    assert results[0].ebay.url == "https://ebay.example/1"
    assert results[0].deal.profit > results[1].deal.profit
    assert results[0].match_confidence == 100.0


def test_scanner_rejects_unmatched_products():
    product = Product(title="Bosch GSR 18V Akkuschrauber", brand="Bosch", ean="1234567890123")
    amazon = MarketOffer("amazon", "https://amazon.example/p", 100.0)
    candidates = [
        (Product(title="Makita Akkuschrauber", brand="Makita", ean="9999999999999"), MarketOffer("ebay", "https://ebay.example/x", 220.0)),
    ]

    assert DealScanner.scan(product, amazon, candidates, ebay_fee_percent=10.0) == []
