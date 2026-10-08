import pytest
import json

from connectors.ebay_browse import EbayBrowseConfig, EbayBrowseConnector


def test_ebay_config_reads_environment(monkeypatch):
    monkeypatch.setenv("EBAY_CLIENT_ID", "client")
    monkeypatch.setenv("EBAY_CLIENT_SECRET", "secret")
    monkeypatch.setenv("EBAY_SEARCH_LIMIT", "7")
    config = EbayBrowseConfig.from_env()
    assert config is not None
    assert config.client_id == "client"
    assert config.limit == 7


def test_ebay_oauth_wraps_malformed_json_response(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return b"{not-json"

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", lambda req, timeout: Response())

    with pytest.raises(RuntimeError, match="eBay OAuth: ungültige API-Antwort"):
        connector._access_token()


def test_ebay_oauth_rejects_non_object_response(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps(["not", "an", "object"]).encode()

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", lambda req, timeout: Response())

    try:
        connector._access_token()
    except RuntimeError as exc:
        assert str(exc) == "eBay OAuth: ungültige JSON-Antwort"
    else:
        raise AssertionError("Expected RuntimeError")


def test_ebay_oauth_rejects_non_string_access_token(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps({"access_token": 12345}).encode()

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", lambda req, timeout: Response())

    try:
        connector._access_token()
    except RuntimeError as exc:
        assert str(exc) == "eBay OAuth: kein Access Token erhalten"
    else:
        raise AssertionError("Expected RuntimeError")


def test_ebay_oauth_strips_access_token_whitespace(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps({"access_token": "  token-with-space  "}).encode()

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", lambda req, timeout: Response())

    assert connector._access_token() == "token-with-space"
    assert connector._token == "token-with-space"


def test_ebay_search_normalizes_browse_response(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))
    connector._token = "token"

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps({"itemSummaries": [
                {"title": "Bosch GSR 18V", "gtin": "1234567890123",
                 "price": {"value": "79.99"}, "itemWebUrl": "https://www.ebay.de/item/1",
                 "shippingOptions": [{"shippingCost": {"value": "4.99"}}],
                 "seller": {"username": "seller1"}},
                {"title": "No price"},
            ]}).encode()

    def fake_urlopen(req, timeout):
        assert "q=Bosch+Akkuschrauber" in req.full_url
        assert req.headers["Authorization"] == "Bearer token"
        return Response()

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", fake_urlopen)
    results = connector.search("Bosch Akkuschrauber")
    assert len(results) == 1
    assert results[0].product.ean == "1234567890123"
    assert results[0].offer.price == 79.99
    assert results[0].offer.seller == "seller1"


def test_ebay_search_empty_query_does_not_call_api(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))
    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
    assert connector.search("   ") == []


def test_ebay_search_uses_lowest_valid_shipping_option(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))
    connector._token = "token"

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps({"itemSummaries": [
                {
                    "title": "Bosch GSR 18V",
                    "price": {"value": "79.99"},
                    "itemWebUrl": "https://www.ebay.de/item/1",
                    "shippingOptions": [
                        {"shippingCost": {"value": "9.99"}},
                        {"shippingCost": {"value": "0.00"}},
                        {"shippingCost": {"value": "invalid"}},
                    ],
                },
            ]}).encode()

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", lambda req, timeout: Response())

    results = connector.search("Bosch Akkuschrauber")

    assert len(results) == 1
    assert results[0].offer.shipping == 0.0


def test_ebay_search_skips_listing_without_actionable_url(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))
    connector._token = "token"

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps({"itemSummaries": [
                {
                    "title": "Bosch GSR 18V",
                    "price": {"value": "79.99"},
                },
                {
                    "title": "Bosch GSR 18V",
                    "price": {"value": "84.99"},
                    "itemWebUrl": "https://www.ebay.de/item/2",
                    "shippingOptions": [{"shippingCost": {"value": "3.99"}}],
                },
            ]}).encode()

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", lambda req, timeout: Response())

    results = connector.search("Bosch Akkuschrauber")

    assert len(results) == 1
    assert results[0].offer.url == "https://www.ebay.de/item/2"


def test_ebay_search_skips_non_actionable_urls(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))
    connector._token = "token"

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps({"itemSummaries": [
                {
                    "title": "Ungültige URL",
                    "price": {"value": "79.99"},
                    "itemWebUrl": "javascript:alert(1)",
                    "shippingOptions": [{"shippingCost": {"value": "2.99"}}],
                },
                {
                    "title": "Fremde Domain",
                    "price": {"value": "79.99"},
                    "itemWebUrl": "https://example.com/itm/123",
                    "shippingOptions": [{"shippingCost": {"value": "2.99"}}],
                },
                {
                    "title": "Relative URL",
                    "price": {"value": "79.99"},
                    "itemWebUrl": "/itm/123",
                    "shippingOptions": [{"shippingCost": {"value": "2.99"}}],
                },
                {
                    "title": "Gültiges Angebot",
                    "price": {"value": "79.99"},
                    "itemWebUrl": "https://www.ebay.de/itm/123",
                    "shippingOptions": [{"shippingCost": {"value": "2.99"}}],
                },
            ]}).encode()

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", lambda req, timeout: Response())

    results = connector.search("Bosch Akkuschrauber")

    assert len(results) == 1
    assert results[0].offer.url == "https://www.ebay.de/itm/123"


def test_ebay_search_skips_zero_or_negative_prices(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))
    connector._token = "token"

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps({"itemSummaries": [
                {
                    "title": "Invalid zero price",
                    "price": {"value": "0"},
                    "itemWebUrl": "https://www.ebay.de/zero",
                    "shippingOptions": [{"shippingCost": {"value": "2.99"}}],
                },
                {
                    "title": "Invalid negative price",
                    "price": {"value": "-5"},
                    "itemWebUrl": "https://www.ebay.de/negative",
                    "shippingOptions": [{"shippingCost": {"value": "2.99"}}],
                },
                {
                    "title": "Valid Bosch GSR",
                    "price": {"value": "79.99"},
                    "itemWebUrl": "https://www.ebay.de/valid",
                    "shippingOptions": [{"shippingCost": {"value": "4.99"}}],
                },
            ]}).encode()

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", lambda req, timeout: Response())

    results = connector.search("Bosch Akkuschrauber")

    assert len(results) == 1
    assert results[0].offer.price == 79.99
    assert results[0].offer.url == "https://www.ebay.de/valid"


def test_ebay_search_skips_listing_without_shipping_data(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))
    connector._token = "token"

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps({"itemSummaries": [
                {
                    "title": "Bosch GSR ohne Versanddaten",
                    "price": {"value": "79.99"},
                    "itemWebUrl": "https://www.ebay.de/item/1",
                },
                {
                    "title": "Bosch GSR mit kostenlosem Versand",
                    "price": {"value": "84.99"},
                    "itemWebUrl": "https://www.ebay.de/item/2",
                    "shippingOptions": [{"shippingCost": {"value": "0.00"}}],
                },
            ]}).encode()

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", lambda req, timeout: Response())

    results = connector.search("Bosch Akkuschrauber")

    assert len(results) == 1
    assert results[0].offer.shipping == 0.0
    assert results[0].offer.url == "https://www.ebay.de/item/2"


def test_ebay_search_skips_listing_with_only_invalid_shipping_costs(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))
    connector._token = "token"

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps({"itemSummaries": [
                {
                    "title": "Bosch GSR",
                    "price": {"value": "79.99"},
                    "itemWebUrl": "https://www.ebay.de/item/1",
                    "shippingOptions": [{"shippingCost": {"value": "invalid"}}],
                },
                {
                    "title": "Bosch GSR gültig",
                    "price": {"value": "84.99"},
                    "itemWebUrl": "https://www.ebay.de/item/2",
                    "shippingOptions": [{"shippingCost": {"value": "4.99"}}],
                },
            ]}).encode()

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", lambda req, timeout: Response())

    results = connector.search("Bosch Akkuschrauber")

    assert len(results) == 1
    assert results[0].offer.shipping == 4.99


def test_ebay_search_skips_auction_only_listing(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))
    connector._token = "token"

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps({"itemSummaries": [
                {
                    "title": "Bosch GSR Auktion",
                    "price": {"value": "49.99"},
                    "itemWebUrl": "https://www.ebay.de/auction",
                    "buyingOptions": ["AUCTION"],
                    "shippingOptions": [{"shippingCost": {"value": "4.99"}}],
                },
                {
                    "title": "Bosch GSR Sofort-Kaufen",
                    "price": {"value": "79.99"},
                    "itemWebUrl": "https://www.ebay.de/fixed",
                    "buyingOptions": ["FIXED_PRICE"],
                    "shippingOptions": [{"shippingCost": {"value": "4.99"}}],
                },
            ]}).encode()

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", lambda req, timeout: Response())

    results = connector.search("Bosch Akkuschrauber")

    assert len(results) == 1
    assert results[0].offer.url == "https://www.ebay.de/fixed"


def test_ebay_search_keeps_listing_when_buying_options_are_missing(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))
    connector._token = "token"

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps({"itemSummaries": [{
                "title": "Bosch GSR ohne BuyingOptions",
                "price": {"value": "79.99"},
                "itemWebUrl": "https://www.ebay.de/item/1",
                "shippingOptions": [{"shippingCost": {"value": "4.99"}}],
            }]}).encode()

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", lambda req, timeout: Response())

    results = connector.search("Bosch Akkuschrauber")

    assert len(results) == 1


def test_ebay_search_skips_non_finite_price_and_shipping(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))
    connector._token = "token"

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps({"itemSummaries": [
                {
                    "title": "Ungültiger Preis",
                    "price": {"value": "Infinity"},
                    "itemWebUrl": "https://www.ebay.de/infinite-price",
                    "shippingOptions": [{"shippingCost": {"value": "4.99"}}],
                },
                {
                    "title": "Ungültiger Versand",
                    "price": {"value": "79.99"},
                    "itemWebUrl": "https://www.ebay.de/infinite-shipping",
                    "shippingOptions": [{"shippingCost": {"value": "Infinity"}}],
                },
                {
                    "title": "Gültiges Angebot",
                    "price": {"value": "84.99"},
                    "itemWebUrl": "https://www.ebay.de/valid",
                    "shippingOptions": [{"shippingCost": {"value": "4.99"}}],
                },
            ]}).encode()

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", lambda req, timeout: Response())

    results = connector.search("Bosch Akkuschrauber")

    assert len(results) == 1
    assert results[0].offer.price == 84.99
    assert results[0].offer.shipping == 4.99

 
def test_ebay_config_rejects_non_integer_limit():
    try:
        EbayBrowseConfig("client", "secret", limit="20")
    except ValueError as exc:
        assert str(exc) == "eBay search limit must be an integer"
    else:
        raise AssertionError("Expected ValueError")


def test_ebay_config_rejects_out_of_range_limit():
    for value in (0, 201):
        try:
            EbayBrowseConfig("client", "secret", limit=value)
        except ValueError as exc:
            assert str(exc) == "eBay search limit must be between 1 and 200"
        else:
            raise AssertionError("Expected ValueError")


def test_ebay_config_rejects_invalid_environment_limit(monkeypatch):
    monkeypatch.setenv("EBAY_CLIENT_ID", "client")
    monkeypatch.setenv("EBAY_CLIENT_SECRET", "secret")
    monkeypatch.setenv("EBAY_SEARCH_LIMIT", "not-a-number")

    try:
        EbayBrowseConfig.from_env()
    except ValueError as exc:
        assert str(exc) == "EBAY_SEARCH_LIMIT must be an integer"
    else:
        raise AssertionError("Expected ValueError")

 
def test_ebay_search_rejects_non_object_response(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))
    connector._token = "token"

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps(["not", "an", "object"]).encode()

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", lambda req, timeout: Response())

    try:
        connector.search("Bosch Akkuschrauber")
    except RuntimeError as exc:
        assert str(exc) == "eBay Browse API: ungültige JSON-Antwort"
    else:
        raise AssertionError("Expected RuntimeError")


def test_ebay_search_rejects_invalid_item_summaries_shape(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))
    connector._token = "token"

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps({"itemSummaries": {"title": "not-a-list"}}).encode()

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", lambda req, timeout: Response())

    try:
        connector.search("Bosch Akkuschrauber")
    except RuntimeError as exc:
        assert str(exc) == "eBay Browse API: itemSummaries muss eine Liste sein"
    else:
        raise AssertionError("Expected RuntimeError")


def test_ebay_search_skips_non_object_item_summary(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))
    connector._token = "token"

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps({
                "itemSummaries": [
                    "invalid-item",
                    {
                        "title": "Bosch GSR",
                        "price": {"value": "79.99"},
                        "itemWebUrl": "https://www.ebay.de/item/1",
                        "shippingOptions": [{"shippingCost": {"value": "4.99"}}],
                    },
                ],
            }).encode()

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", lambda req, timeout: Response())

    results = connector.search("Bosch Akkuschrauber")

    assert len(results) == 1
    assert results[0].offer.price == 79.99


def test_ebay_search_skips_boolean_price_and_shipping_values(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))
    connector._token = "token"

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps({"itemSummaries": [
                {
                    "title": "Boolean price",
                    "price": {"value": True},
                    "itemWebUrl": "https://www.ebay.de/bool-price",
                    "shippingOptions": [{"shippingCost": {"value": 4.99}}],
                },
                {
                    "title": "Boolean shipping",
                    "price": {"value": 79.99},
                    "itemWebUrl": "https://www.ebay.de/bool-shipping",
                    "shippingOptions": [{"shippingCost": {"value": False}}],
                },
                {
                    "title": "Valid offer",
                    "price": {"value": 84.99},
                    "itemWebUrl": "https://www.ebay.de/valid",
                    "shippingOptions": [{"shippingCost": {"value": 4.99}}],
                },
            ]}).encode()

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", lambda req, timeout: Response())

    results = connector.search("Bosch Akkuschrauber")

    assert len(results) == 1
    assert results[0].offer.price == 84.99
    assert results[0].offer.shipping == 4.99


def test_ebay_search_ignores_boolean_competition_count(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))
    connector._token = "token"

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps({
                "total": True,
                "itemSummaries": [{
                    "title": "Bosch GSR",
                    "price": {"value": "79.99"},
                    "itemWebUrl": "https://www.ebay.de/item/1",
                    "shippingOptions": [{"shippingCost": {"value": "4.99"}}],
                }],
            }).encode()

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", lambda req, timeout: Response())

    results = connector.search("Bosch Akkuschrauber")

    assert len(results) == 1
    assert results[0].offer.competition_count is None


def test_ebay_search_rejects_invalid_competition_count(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))
    connector._token = "token"

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps({
                "total": -5,
                "itemSummaries": [{
                    "title": "Bosch GSR",
                    "price": {"value": "79.99"},
                    "itemWebUrl": "https://www.ebay.de/item/1",
                    "shippingOptions": [{"shippingCost": {"value": "4.99"}}],
                }],
            }).encode()

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", lambda req, timeout: Response())

    results = connector.search("Bosch Akkuschrauber")

    assert len(results) == 1
    assert results[0].offer.competition_count is None


def test_ebay_connector_rejects_invalid_timeout():
    config = EbayBrowseConfig("id", "secret")

    for timeout in (0, -1, float("nan"), float("inf"), True):
        try:
            EbayBrowseConnector(config, timeout=timeout)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected ValueError for timeout={timeout!r}")


def test_ebay_connector_accepts_positive_timeout():
    connector = EbayBrowseConnector(EbayBrowseConfig("id", "secret"), timeout=7.5)
    assert connector.timeout == 7.5
