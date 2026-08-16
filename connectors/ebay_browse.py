from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from urllib import parse, request

from connectors.market_data import MarketListing
from core.models import MarketOffer, Product


@dataclass(frozen=True, slots=True)
class EbayBrowseConfig:
    client_id: str
    client_secret: str
    marketplace_id: str = "EBAY_DE"
    locale: str = "de-DE"
    sandbox: bool = False
    limit: int = 20

    @classmethod
    def from_env(cls) -> "EbayBrowseConfig | None":
        client_id = os.getenv("EBAY_CLIENT_ID", "")
        client_secret = os.getenv("EBAY_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            return None
        return cls(
            client_id=client_id,
            client_secret=client_secret,
            marketplace_id=os.getenv("EBAY_MARKETPLACE_ID", "EBAY_DE"),
            locale=os.getenv("EBAY_LOCALE", "de-DE"),
            sandbox=os.getenv("EBAY_SANDBOX", "0").lower() in {"1", "true", "yes"},
            limit=max(1, min(200, int(os.getenv("EBAY_SEARCH_LIMIT", "20")))),
        )


class EbayBrowseConnector:
    """Production eBay Browse API adapter using application OAuth."""

    def __init__(self, config: EbayBrowseConfig, timeout: float = 15.0):
        self.config = config
        self.timeout = timeout
        self._token: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.config.client_id and self.config.client_secret)

    @property
    def base_url(self) -> str:
        return "https://api.sandbox.ebay.com" if self.config.sandbox else "https://api.ebay.com"

    def _access_token(self) -> str:
        credentials = base64.b64encode(f"{self.config.client_id}:{self.config.client_secret}".encode()).decode()
        payload = parse.urlencode({
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope",
        }).encode()
        req = request.Request(
            f"{self.base_url}/identity/v1/oauth2/token",
            data=payload,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=self.timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        token = data.get("access_token")
        if not token:
            raise RuntimeError("eBay OAuth: kein Access Token erhalten")
        self._token = token
        return token

    def search(self, query: str) -> list[MarketListing]:
        query = query.strip()
        if not query:
            return []
        token = self._token or self._access_token()
        params = parse.urlencode({"q": query, "limit": self.config.limit})
        req = request.Request(
            f"{self.base_url}/buy/browse/v1/item_summary/search?{params}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept-Language": self.config.locale,
                "X-EBAY-C-MARKETPLACE-ID": self.config.marketplace_id,
            },
            method="GET",
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            self._token = None
            raise RuntimeError(f"eBay Browse API: {exc}") from exc

        results: list[MarketListing] = []
        for item in data.get("itemSummaries", []):
            try:
                price = float((item.get("price") or {})["value"])
            except (KeyError, TypeError, ValueError):
                continue
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            gtin = item.get("gtin")
            product = Product(title=title, ean=str(gtin) if gtin else None)
            offer = MarketOffer(
                source="ebay",
                url=str(item.get("itemWebUrl") or ""),
                price=price,
                seller=str((item.get("seller") or {}).get("username") or ""),
            )
            results.append(MarketListing(product=product, offer=offer))
        return results
