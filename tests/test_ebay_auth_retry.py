import json
from urllib.error import HTTPError

from connectors.ebay_browse import EbayBrowseConfig, EbayBrowseConnector


class Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def test_ebay_search_refreshes_token_once_after_401(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))
    connector._token = "expired-token"
    calls = []

    def fake_urlopen(req, timeout):
        calls.append((req.full_url, req.headers.get("Authorization")))
        if "/identity/v1/oauth2/token" in req.full_url:
            return Response({"access_token": "fresh-token"})
        if req.headers["Authorization"] == "Bearer expired-token":
            raise HTTPError(req.full_url, 401, "Unauthorized", {}, None)
        return Response({"itemSummaries": []})

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", fake_urlopen)

    assert connector.search("Bosch Akkuschrauber") == []
    assert calls[0][1] == "Bearer expired-token"
    assert calls[1][0].endswith("/identity/v1/oauth2/token")
    assert calls[2][1] == "Bearer fresh-token"
    assert connector._token == "fresh-token"


def test_ebay_search_does_not_retry_non_401_http_error(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))
    connector._token = "token"

    def fake_urlopen(req, timeout):
        raise HTTPError(req.full_url, 403, "Forbidden", {}, None)

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", fake_urlopen)

    try:
        connector.search("Bosch Akkuschrauber")
    except RuntimeError as exc:
        assert "eBay Browse API" in str(exc)
        assert "HTTP Error 403" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")

    assert connector._token is None

    
def test_ebay_search_retries_once_after_429(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))
    connector._token = "token"
    calls = []

    def fake_urlopen(req, timeout):
        calls.append(req.headers.get("Authorization"))
        if len(calls) == 1:
            raise HTTPError(req.full_url, 429, "Too Many Requests", {}, None)
        return Response({"itemSummaries": []})

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", fake_urlopen)

    assert connector.search("Bosch Akkuschrauber") == []
    assert calls == ["Bearer token", "Bearer token"]
    assert connector._token == "token"


def test_ebay_search_retries_once_after_server_error(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))
    connector._token = "token"
    calls = []

    def fake_urlopen(req, timeout):
        calls.append(req.headers.get("Authorization"))
        if len(calls) == 1:
            raise HTTPError(req.full_url, 503, "Service Unavailable", {}, None)
        return Response({"itemSummaries": []})

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", fake_urlopen)

    assert connector.search("Bosch Akkuschrauber") == []
    assert calls == ["Bearer token", "Bearer token"]


def test_ebay_search_fails_after_transient_error_retry(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))
    connector._token = "token"

    def fake_urlopen(req, timeout):
        raise HTTPError(req.full_url, 503, "Service Unavailable", {}, None)

    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", fake_urlopen)

    try:
        connector.search("Bosch Akkuschrauber")
    except RuntimeError as exc:
        assert "eBay Browse API" in str(exc)
        assert "HTTP Error 503" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")

    assert connector._token is None


def test_ebay_search_honors_retry_after_header(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))
    connector._token = "token"
    delays = []
    calls = []

    def fake_sleep(delay):
        delays.append(delay)

    def fake_urlopen(req, timeout):
        calls.append(req.headers.get("Authorization"))
        if len(calls) == 1:
            raise HTTPError(
                req.full_url,
                429,
                "Too Many Requests",
                {"Retry-After": "2.5"},
                None,
            )
        return Response({"itemSummaries": []})

    monkeypatch.setattr("connectors.ebay_browse.time.sleep", fake_sleep)
    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", fake_urlopen)

    assert connector.search("Bosch Akkuschrauber") == []
    assert delays == [2.5]
    assert len(calls) == 2


def test_ebay_search_ignores_invalid_retry_after_header(monkeypatch):
    connector = EbayBrowseConnector(EbayBrowseConfig("client", "secret"))
    connector._token = "token"
    delays = []

    def fake_sleep(delay):
        delays.append(delay)

    calls = []

    def fake_urlopen(req, timeout):
        calls.append(req.headers.get("Authorization"))
        if len(calls) == 1:
            raise HTTPError(
                req.full_url,
                503,
                "Service Unavailable",
                {"Retry-After": "not-a-number"},
                None,
            )
        return Response({"itemSummaries": []})

    monkeypatch.setattr("connectors.ebay_browse.time.sleep", fake_sleep)
    monkeypatch.setattr("connectors.ebay_browse.request.urlopen", fake_urlopen)

    assert connector.search("Bosch Akkuschrauber") == []
    assert delays == []
