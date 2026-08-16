from run_live import build_live_runner


def test_live_runner_requires_telegram_configuration(monkeypatch):
    monkeypatch.delenv("PROFITPILOT_TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("PROFITPILOT_TELEGRAM_CHAT_ID", raising=False)
    runner = build_live_runner()
    assert runner is None
