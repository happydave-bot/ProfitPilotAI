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
                 "price": {"value": "79.99"}, "itemWebUrl": "https://ebay.example/item/1",
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
                    "itemWebUrl": "https://ebay.example/item/1",
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
                    "itemWebUrl": "https://ebay.example/item/2",
                },
            ]}).encode()

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", lambda req, timeout: Response())

    results = connector.search("Bosch Akkuschrauber")

    assert len(results) == 1
    assert results[0].offer.url == "https://ebay.example/item/2"


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
                    "itemWebUrl": "https://ebay.example/zero",
                },
                {
                    "title": "Invalid negative price",
                    "price": {"value": "-5"},
                    "itemWebUrl": "https://ebay.example/negative",
                },
                {
                    "title": "Valid Bosch GSR",
                    "price": {"value": "79.99"},
                    "itemWebUrl": "https://ebay.example/valid",
                },
            ]}).encode()

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", lambda req, timeout: Response())

    results = connector.search("Bosch Akkuschrauber")

    assert len(results) == 1
    assert results[0].offer.price == 79.99
    assert results[0].offer.url == "https://ebay.example/valid"
