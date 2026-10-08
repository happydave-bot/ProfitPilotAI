[object Object]

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
                    "itemWebUrl": "https://ebay.example/item/1",
                },
                {
                    "title": "Bosch GSR mit kostenlosem Versand",
                    "price": {"value": "84.99"},
                    "itemWebUrl": "https://ebay.example/item/2",
                    "shippingOptions": [{"shippingCost": {"value": "0.00"}}],
                },
            ]}).encode()

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", lambda req, timeout: Response())

    results = connector.search("Bosch Akkuschrauber")

    assert len(results) == 1
    assert results[0].offer.shipping == 0.0
    assert results[0].offer.url == "https://ebay.example/item/2"


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
                    "itemWebUrl": "https://ebay.example/item/1",
                    "shippingOptions": [{"shippingCost": {"value": "invalid"}}],
                },
                {
                    "title": "Bosch GSR gültig",
                    "price": {"value": "84.99"},
                    "itemWebUrl": "https://ebay.example/item/2",
                    "shippingOptions": [{"shippingCost": {"value": "4.99"}}],
                },
            ]}).encode()

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", lambda req, timeout: Response())

    results = connector.search("Bosch Akkuschrauber")

    assert len(results) == 1
    assert results[0].offer.shipping == 4.99
