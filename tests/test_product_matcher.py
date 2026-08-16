from core.product_matcher import ProductMatcher
from core.models import Product


def test_match_by_ean():
    a = Product(title="Bosch GSR 18V", brand="Bosch", ean="1234567890123")
    b = Product(title="Completely different title", brand="Other", ean="1234567890123")
    result = ProductMatcher.match(a, b)
    assert result.is_match
    assert result.confidence == 100.0


def test_mismatch_by_strong_identifiers():
    a = Product(title="Bosch GSR 18V", brand="Bosch", ean="1234567890123")
    b = Product(title="Bosch GSR 18V", brand="Bosch", ean="9999999999999")
    result = ProductMatcher.match(a, b)
    assert not result.is_match
    assert result.confidence == 0.0


def test_title_and_brand_can_match_without_ean():
    a = Product(title="Bosch GSR 18V Akkuschrauber", brand="Bosch")
    b = Product(title="Bosch GSR 18V Professional Akkuschrauber", brand="Bosch")
    result = ProductMatcher.match(a, b)
    assert result.is_match
    assert result.confidence >= 95.0
