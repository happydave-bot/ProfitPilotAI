from run_live import build_live_runner


def test_live_runner_requires_telegram_configuration(monkeypatch):
    monkeypatch.delenv("PROFITPILOT_TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("PROFITPILOT_TELEGRAM_CHAT_ID", raising=False)
    runner = build_live_runner()
    assert runner is None



def test_run_live_imports_dotenv_loader():
    import run_live

    assert callable(run_live.load_dotenv)



def test_ebay_listing_product_keeps_brand_and_mpn():
    from connectors.ebay_browse import EbayBrowseConnector, EbayBrowseConfig

    connector = EbayBrowseConnector(EbayBrowseConfig("id", "secret"))
    connector._access_token = "token"

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return b'{"itemSummaries":[{"title":"Bosch GSR 18V-65","gtin":"4000000000001","brand":"Bosch","mpn":"06019N0E2B","price":{"value":"85.00"},"itemWebUrl":"https://ebay.example"}]}'

    import connectors.ebay_browse as module
    original = module.request.urlopen
    module.request.urlopen = lambda *args, **kwargs: Response()
    try:
        listing = connector.search("Bosch GSR 18V-65")[0]
    finally:
        module.request.urlopen = original

    assert listing.product.brand == "Bosch"
    assert listing.product.model == "06019N0E2B"
    assert listing.product.ean == "4000000000001"
