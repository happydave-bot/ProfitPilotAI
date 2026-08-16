from core.batch_scanner import BatchScanConfig, BatchScanner
from core.models import MarketOffer, Product


def product(title, ean):
    return Product(title=title, brand="Bosch", ean=ean)


def amazon_for(p):
    prices = {"111": 40.0, "222": 50.0, "333": 40.0}
    return MarketOffer(source="amazon", url="https://amazon.example", price=prices[p.ean])


def ebay_for(p):
    prices = {"111": 80.0, "222": 100.0, "333": 75.0}
    return [(p, MarketOffer(source="ebay", url="https://ebay.example", price=prices[p.ean]))]


def test_batch_scanner_ranks_all_products_by_profit():
    products = [product("A", "111"), product("B", "222"), product("C", "333")]
    results = BatchScanner.scan(products, amazon_for, ebay_for)
    assert len(results) == 3
    assert results[0].product.ean == "222"
    assert results[0].deal.profit > results[1].deal.profit > results[2].deal.profit


def test_batch_scanner_applies_profit_roi_filters_and_limit():
    products = [product("A", "111"), product("B", "222"), product("C", "333")]
    results = BatchScanner.scan(
        products,
        amazon_for,
        ebay_for,
        BatchScanConfig(min_profit=20.0, min_roi=40.0, max_results=1),
    )
    assert len(results) == 1
    assert results[0].product.ean == "222"
