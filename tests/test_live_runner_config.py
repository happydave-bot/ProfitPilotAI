from run_live import build_live_runner


def test_live_runner_requires_all_credentials(monkeypatch):
    for name in (
        "PROFITPILOT_TELEGRAM_TOKEN",
        "PROFITPILOT_TELEGRAM_CHAT_ID",
        "AMAZON_CREATORS_CLIENT_ID",
        "AMAZON_CREATORS_CLIENT_SECRET",
        "AMAZON_CREATORS_REFRESH_TOKEN",
        "EBAY_CLIENT_ID",
        "EBAY_CLIENT_SECRET",
        "PROFITPILOT_QUERY",
    ):
        monkeypatch.delenv(name, raising=False)

    assert build_live_runner() is None



def test_live_runner_can_start_in_explicit_ebay_only_mode(monkeypatch):
    for name in (
        "PROFITPILOT_TELEGRAM_TOKEN",
        "PROFITPILOT_TELEGRAM_CHAT_ID",
        "AMAZON_CREATORS_CLIENT_ID",
        "AMAZON_CREATORS_CLIENT_SECRET",
        "AMAZON_PARTNER_TAG",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PROFITPILOT_EBAY_ONLY", "1")
    monkeypatch.setenv("EBAY_CLIENT_ID", "test-id")
    monkeypatch.setenv("EBAY_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("PROFITPILOT_QUERY", "Bosch Akkuschrauber")

    runner = build_live_runner(dry_run=True)

    assert runner is not None
    assert runner.scan() == []
