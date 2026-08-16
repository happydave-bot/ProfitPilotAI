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
