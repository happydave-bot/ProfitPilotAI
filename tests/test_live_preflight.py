from core.live_preflight import validate_live_environment


def set_credentials(monkeypatch):
    monkeypatch.setenv("AMAZON_CREATORS_CLIENT_ID", "amazon-id")
    monkeypatch.setenv("AMAZON_CREATORS_CLIENT_SECRET", "amazon-secret")
    monkeypatch.setenv("AMAZON_PARTNER_TAG", "tag-20")
    monkeypatch.setenv("EBAY_CLIENT_ID", "ebay-id")
    monkeypatch.setenv("EBAY_CLIENT_SECRET", "ebay-secret")
    monkeypatch.setenv("PROFITPILOT_QUERY", "Bosch Akkuschrauber")


def test_preflight_accepts_complete_configuration(monkeypatch):
    set_credentials(monkeypatch)
    result = validate_live_environment()
    assert result.ok
    assert "genau ein Suchbegriff" in result.summary()


def test_preflight_reports_missing_credentials(monkeypatch):
    for name in (
        "AMAZON_CREATORS_CLIENT_ID",
        "AMAZON_CREATORS_CLIENT_SECRET",
        "AMAZON_PARTNER_TAG",
        "EBAY_CLIENT_ID",
        "EBAY_CLIENT_SECRET",
        "PROFITPILOT_QUERY",
        "PROFITPILOT_QUERIES",
    ):
        monkeypatch.delenv(name, raising=False)
    result = validate_live_environment()
    assert not result.ok
    assert "AMAZON_CREATORS_CLIENT_ID" in result.missing
    assert "EBAY_CLIENT_ID" in result.missing


def test_preflight_rejects_invalid_fee(monkeypatch):
    set_credentials(monkeypatch)
    monkeypatch.setenv("PROFITPILOT_EBAY_FEE_PERCENT", "abc")
    result = validate_live_environment()
    assert not result.ok
    assert "PROFITPILOT_EBAY_FEE_PERCENT (Zahl)" in result.missing
