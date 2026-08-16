from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from connectors.market_data import MarketListing
from core.deal_scanner import DealScanner, ScanCandidate
from core.models import MarketOffer, Product


@dataclass(frozen=True, slots=True)
class LiveScanResult:
    product: Product
    amazon_offer: MarketOffer
    deals: tuple[ScanCandidate, ...]


class LiveMarketPipeline:
    """Bridge real Amazon/eBay listings into the existing deal-scanner core."""

    def __init__(self, amazon_connector, ebay_connector, ebay_fee_percent: float = 12.9, packaging_cost: float = 2.0):
        self.amazon = amazon_connector
        self.ebay = ebay_connector
        self.ebay_fee_percent = ebay_fee_percent
        self.packaging_cost = packaging_cost

    def scan(self, query: str) -> list[LiveScanResult]:
        amazon_listings = list(self.amazon.search(query))
        results: list[LiveScanResult] = []
        for listing in amazon_listings:
            candidates = self.ebay.search(listing.product.title)
            ebay_pairs = [(item.product, item.offer) for item in candidates]
            deals = tuple(
                DealScanner.scan(
                    listing.product,
                    listing.offer,
                    ebay_pairs,
                    ebay_fee_percent=self.ebay_fee_percent,
                    packaging_cost=self.packaging_cost,
                )
            )
            if deals:
                results.append(LiveScanResult(listing.product, listing.offer, deals))
        return results
