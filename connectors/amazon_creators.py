from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from urllib import request

from connectors.market_data import MarketListing
from core.models import MarketOffer, Product


@dataclass(frozen=True, slots=True)
class AmazonCreatorsConfig:
    client_id: str
    client_secret: str
    partner_tag: str
    marketplace: str = "www.amazon.de"
    token_endpoint: str = "https://api.amazon.co.uk/auth/o2/token"
    limit: int = 10

    @classmethod
    def from_env(cls) -> "AmazonCreatorsConfig | None":
        client_id = os.getenv("AMAZON_CREATORS_CLIENT_ID", "")
        client_secret = os.getenv("AMAZON_CREATORS_CLIENT_SECRET", "")
        partner_tag = os.getenv("AMAZON_PARTNER_TAG", "")
        if not client_id or not client_secret or not partner_tag:
            return None
        return cls(
            client_id=client_id,
            client_secret=client_secret,
            partner_tag=partner_tag,
            marketplace=os.getenv("AMAZON_MARKETPLACE", "www.amazon.de"),
            token_endpoint=os.getenv("AMAZON_TOKEN_ENDPOINT", "https://api.amazon.co.uk/auth/o2/token"),
            limit=max(1, min(10, int(os.getenv("AMAZON_SEARCH_LIMIT", "10")))),
        )


class AmazonCreatorsConnector:
    """Amazon Creators API SearchItems adapter for the German marketplace."""

    def __init__(self, config: AmazonCreatorsConfig, timeout: float = 15.0):
        self.config = config
        self.timeout = timeout
        self._token: str | None = None
        self._token_expires_at = 0.0

    @property
    def configured(self) -> bool:
        return bool(self.config.client_id and self.config.client_secret and self.config.partner_tag)

    def _access_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 30:
            return self._token
        payload = json.dumps({
            "grant_type": "client_credentials",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "scope": "creatorsapi::default",
        }).encode()
        req = request.Request(
            self.config.token_endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise RuntimeError(f"Amazon Creators OAuth: {exc}") from exc
        token = data.get("access_token")
        if not token:
            raise RuntimeError("Amazon Creators OAuth: kein Access Token erhalten")
        self._token = token
        self._token_expires_at = time.time() + float(data.get("expires_in", 3600))
        return token

    def search(self, query: str) -> list[MarketListing]:
        query = query.strip()
        if not query:
            return []
        token = self._access_token()
        payload = {
            "keywords": query,
            "searchIndex": "All",
            "partnerTag": self.config.partner_tag,
            "partnerType": "Associates",
            "marketplace": self.config.marketplace,
            "resources": [
                "itemInfo.title",
                "itemInfo.byLineInfo",
                "itemInfo.externalIds",
                "itemInfo.manufactureInfo",
                "offersV2.listings.price",
                "offersV2.listings.merchantInfo",
            ],
        }
        req = request.Request(
            "https://creatorsapi.amazon/catalog/v1/searchItems",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "x-marketplace": self.config.marketplace,
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise RuntimeError(f"Amazon Creators API: {exc}") from exc

        results: list[MarketListing] = []
        for item in data.get("searchResult", {}).get("items", [])[: self.config.limit]:
            title = str(((item.get("itemInfo") or {}).get("title") or {}).get("displayValue") or "").strip()
            asin = item.get("asin")
            if not title or not asin:
                continue
            item_info = item.get("itemInfo") or {}
            byline = item_info.get("byLineInfo") or {}
            brand_value = (byline.get("brand") or {}).get("displayValue")
            brand = str(brand_value or "").strip()

            external_ids = item_info.get("externalIds") or {}
            eans = (external_ids.get("eans") or {}).get("displayValues") or []
            ean = str(eans[0]).strip() if eans else None

            manufacture = item_info.get("manufactureInfo") or {}
            model_value = (manufacture.get("model") or {}).get("displayValue")
            part_number_value = (manufacture.get("itemPartNumber") or {}).get("displayValue")
            model = str(model_value or part_number_value or "").strip() or None
            listings = ((item.get("offersV2") or {}).get("listings") or [])
            priced: list[tuple[float, dict]] = []
            for entry in listings:
                money = (entry.get("price") or {}).get("money") or {}
                try:
                    amount = float(money["amount"])
                except (KeyError, TypeError, ValueError):
                    continue
                priced.append((amount, entry))
            if not priced:
                continue
            price, selected = min(priced, key=lambda pair: pair[0])
            merchant = (selected.get("merchantInfo") or {}).get("name") or ""
            product = Product(title=title, brand=brand, asin=str(asin), ean=ean, model=model)
            detail_url = str(item.get("detailPageURL") or "").strip()
            offer = MarketOffer(source="amazon", url=detail_url or f"https://www.amazon.de/dp/{asin}", price=price, seller=str(merchant))
            results.append(MarketListing(product=product, offer=offer))
        return results
