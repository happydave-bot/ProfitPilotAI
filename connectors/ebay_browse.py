from __future__ import annotations

import base64
import json
import math
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

    def __post_init__(self):
        if isinstance(self.limit, bool) or not isinstance(self.limit, int):
            raise ValueError("eBay search limit must be an integer")
        if self.limit < 1 or self.limit > 200:
            raise ValueError("eBay search limit must be between 1 and 200")

    @classmethod
    def from_env(cls) -> "EbayBrowseConfig | None":
        client_id = os.getenv("EBAY_CLIENT_ID", "")
        client_secret = os.getenv("EBAY_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            return None
        raw_limit = os.getenv("EBAY_SEARCH_LIMIT", "20").strip()
        try:
            limit = int(raw_limit)
        except ValueError as exc:
            raise ValueError("EBAY_SEARCH_LIMIT must be an integer") from exc
        return cls(
            client_id=client_id,
            client_secret=client_secret,
            marketplace_id=os.getenv("EBAY_MARKETPLACE_ID", "EBAY_DE"),
            locale=os.getenv("EBAY_LOCALE", "de-DE"),
            sandbox=os.getenv("EBAY_SANDBOX", "0").lower() in {"1", "true", "yes"},
            limit=limit,
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

        if not isinstance(data, dict):
            raise RuntimeError("eBay Browse API: ungültige JSON-Antwort")

        raw_item_summaries = data.get("itemSummaries", [])
        if raw_item_summaries is None:
            raw_item_summaries = []
        if not isinstance(raw_item_summaries, list):
            raise RuntimeError("eBay Browse API: itemSummaries muss eine Liste sein")

        results: list[MarketListing] = []
        total_results = data.get("total")
        try:
            parsed_total = int(total_results) if total_results is not None else None
        except (TypeError, ValueError):
            parsed_total = None
        competition_count = parsed_total if parsed_total is not None and parsed_total >= 0 else None

        for item in raw_item_summaries:
            if not isinstance(item, dict):
                continue
            try:
                price = float((item.get("price") or {})["value"])
            except (KeyError, TypeError, ValueError):
                continue
            if not math.isfinite(price) or price <= 0:
                continue
            title = str(item.get("title") or "").strip()
            item_url = str(item.get("itemWebUrl") or "").strip()
            buying_options = item.get("buyingOptions")
            if isinstance(buying_options, list) and buying_options:
                normalized_buying_options = {
                    str(option).strip().upper()
                    for option in buying_options
                    if str(option).strip()
                }
                if normalized_buying_options and "FIXED_PRICE" not in normalized_buying_options:
                    continue
            if not title or not item_url:
                continue
            gtin = item.get("gtin")
            brand = str(item.get("brand") or "").strip()
            mpn = str(item.get("mpn") or "").strip()
            product = Product(
                title=title,
                brand=brand,
                ean=str(gtin) if gtin else None,
                model=mpn or None,
            )
            shipping_options = item.get("shippingOptions")
            if not isinstance(shipping_options, list) or not shipping_options:
                continue

            shipping_costs: list[float] = []
            for option in shipping_options:
                if not isinstance(option, dict):
                    continue
                raw_cost = (option.get("shippingCost") or {}).get("value")
                try:
                    cost = float(raw_cost)
                except (TypeError, ValueError):
                    continue
                if math.isfinite(cost) and cost >= 0:
                    shipping_costs.append(cost)
            if not shipping_costs:
                continue

            shipping = min(shipping_costs)

            offer = MarketOffer(
                source="ebay",
                url=item_url,
                price=price,
                shipping=shipping,
                seller=str((item.get("seller") or {}).get("username") or ""),
                competition_count=competition_count,
            )
            results.append(MarketListing(product=product, offer=offer))
        return results
