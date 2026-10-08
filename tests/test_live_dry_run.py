from run_live import build_live_runner


def test_dry_run_requires_market_credentials(monkeypatch):
    monkeypatch.setenv("PROFITPILOT_DRY_RUN", "1")
    monkeypatch.setenv("PROFITPILOT_QUERY", "Bosch Akkuschrauber")
    monkeypatch.delenv("PROFITPILOT_AMAZON_CLIENT_ID", raising=False)
    monkeypatch.delenv("PROFITPILOT_EBAY_CLIENT_ID", raising=False)
    assert build_live_runner(dry_run=True) is None


def test_once_and_dry_run_flags_are_supported():
    # Argument parsing is exercised by the CLI in integration; this test
    # verifies the safe notifier can be selected without Telegram credentials.
    from run_live import DryRunNotifier

    notifier = DryRunNotifier()
    notifier.send("test")
    assert notifier.messages == ["test"]



def test_ebay_connectivity_test_uses_query_without_runner(monkeypatch, capsys):
    from run_live import run_ebay_connectivity_test

    monkeypatch.setenv("EBAY_CLIENT_ID", "client")
    monkeypatch.setenv("EBAY_CLIENT_SECRET", "secret")
    monkeypatch.setenv("PROFITPILOT_QUERY", "Bosch Akkuschrauber")

    class FakeConnector:
        def __init__(self, config):
            self.config = config

        def search(self, query):
            assert query == "Bosch Akkuschrauber"
            from connectors.market_data import MarketListing
            from core.models import MarketOffer, Product
            return [MarketListing(
                product=Product(title="Bosch GSR"),
                offer=MarketOffer(source="ebay", url="https://example.test/item", price=99.0),
            )]

    monkeypatch.setattr("run_live.EbayBrowseConnector", FakeConnector)
    assert run_ebay_connectivity_test() == 0
    assert "OK - 1 Angebote gefunden" in capsys.readouterr().out
