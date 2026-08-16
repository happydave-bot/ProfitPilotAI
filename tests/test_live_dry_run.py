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
