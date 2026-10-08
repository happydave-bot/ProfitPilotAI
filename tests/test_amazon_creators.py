import json

from connectors.amazon_creators import AmazonCreatorsConfig, AmazonCreatorsConnector


def test_amazon_config_reads_environment(monkeypatch):
    monkeypatch.setenv("AMAZON_CREATORS_CLIENT_ID", "client")
    monkeypatch.setenv("AMAZON_CREATORS_CLIENT_SECRET", "secret")
    monkeypatch.setenv("AMAZON_PARTNER_TAG", "tag-20")
    config = AmazonCreatorsConfig.from_env()
    assert config is not None
    assert config.marketplace == "www.amazon.de"


def test_amazon_search_normalizes_creators_response(monkeypatch):
    monkeypatch.setattr(
        "connectors.amazon_creators.request.urlopen",
        lambda req, timeout: _Response({"access_token": "token", "expires_in": 3600}) if "/auth/o2/token" in req.full_url else _Response({
            "searchResult": {"items": [{
                "asin": "B123",
                "detailPageURL": "https://www.amazon.de/dp/B123?tag=tag-20",
                "itemInfo": {
                    "title": {"displayValue": "Bosch Akkuschrauber"},
                    "byLineInfo": {"brand": {"displayValue": "Bosch"}},
                    "externalIds": {"eans": {"displayValues": ["4000000000001"]}},
                    "manufactureInfo": {
                        "model": {"displayValue": "GSR-18V-65"},
                        "itemPartNumber": {"displayValue": "06019N0E2B"},
                    },
                },
                "offersV2": {"listings": [{"price": {"money": {"amount": "79.99"}}, "merchantInfo": {"name": "Amazon"}}]},
            }]}
        }),
    )
    config = AmazonCreatorsConfig("client", "secret", "tag-20")
    results = AmazonCreatorsConnector(config).search("Bosch Akkuschrauber")
    assert len(results) == 1
    assert results[0].product.asin == "B123"
    assert results[0].product.brand == "Bosch"
    assert results[0].product.ean == "4000000000001"
    assert results[0].product.model == "GSR-18V-65"
    assert results[0].offer.price == 79.99
    assert results[0].offer.source == "amazon"
    assert results[0].offer.url == "https://www.amazon.de/dp/B123?tag=tag-20"


def test_amazon_empty_query_does_not_call_api(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("API must not be called")
    monkeypatch.setattr("connectors.amazon_creators.request.urlopen", fail)
    config = AmazonCreatorsConfig("client", "secret", "tag-20")
    assert AmazonCreatorsConnector(config).search("   ") == []


class _Response:
    status = 200
    def __init__(self, data):
        self.data = data
    def read(self):
        return json.dumps(self.data).encode()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False


def test_amazon_search_selects_lowest_valid_offer():
    monkeypatch = None
    original = __import__("connectors.amazon_creators", fromlist=["request"]).request.urlopen

    def fake_urlopen(req, timeout):
        if "/auth/o2/token" in req.full_url:
            return _Response({"access_token": "token", "expires_in": 3600})
        return _Response({
            "searchResult": {"items": [{
                "asin": "B456",
                "detailPageURL": "https://www.amazon.de/dp/B456",
                "itemInfo": {"title": {"displayValue": "Bosch GSR 18V-65"}},
                "offersV2": {"listings": [
                    {"price": {"money": {"amount": "89.99"}}, "merchantInfo": {"name": "Amazon"}},
                    {"price": {"money": {"amount": "74.50"}}, "merchantInfo": {"name": "Drittanbieter"}},
                    {"price": {"money": {"amount": "not-a-number"}}, "merchantInfo": {"name": "Invalid"}},
                ]},
            }]}
        })

    module = __import__("connectors.amazon_creators", fromlist=["request"])
    module.request.urlopen = fake_urlopen
    try:
        results = AmazonCreatorsConnector(AmazonCreatorsConfig("client", "secret", "tag-20")).search("Bosch")
    finally:
        module.request.urlopen = original

    assert len(results) == 1
    assert results[0].offer.price == 74.50
    assert results[0].offer.seller == "Drittanbieter"
