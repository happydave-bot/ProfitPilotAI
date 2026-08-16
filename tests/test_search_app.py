from ui.search_app import scan_product


def test_scan_product_requires_query():
    assert scan_product(" ") == "Bitte ein Produkt eingeben."


def test_scan_product_returns_deal_for_query():
    result = scan_product("Bosch Akkuschrauber")
    assert "Bosch Akkuschrauber" in result
    assert "Profit" in result
    assert "ROI" in result
