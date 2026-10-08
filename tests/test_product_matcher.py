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


def test_mismatch_by_model_is_rejected():
    a = Product(
        title="Bosch GSR 18V-65",
        brand="Bosch",
        model="06019N0E2B",
    )
    b = Product(
        title="Bosch GSR 18V-65",
        brand="Bosch",
        model="06019N0E2C",
    )
    result = ProductMatcher.match(a, b)
    assert not result.is_match
    assert result.confidence == 0.0
    assert result.reasons == ("Modell stimmt nicht überein",)


def test_matching_model_is_accepted_as_exact_identifier():
    a = Product(
        title="Bosch GSR 18V-65",
        brand="Bosch",
        model="06019N0E2B",
    )
    b = Product(
        title="Completely different title",
        brand="Other",
        model="06019N0E2B",
    )
    result = ProductMatcher.match(a, b)
    assert result.is_match
    assert result.confidence == 100.0
