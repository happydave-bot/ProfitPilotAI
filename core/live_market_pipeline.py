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

    @staticmethod
    def _ebay_queries(product: Product) -> tuple[str, ...]:
        values = [product.ean, product.model, product.title]
        queries: list[str] = []
        for value in values:
            normalized = str(value or "").strip()
            if normalized and normalized not in queries:
                queries.append(normalized)
        return tuple(queries)

    def _scan_ebay_candidates(self, listing: MarketListing) -> tuple[ScanCandidate, ...]:
        for ebay_query in self._ebay_queries(listing.product):
            candidates = self.ebay.search(ebay_query)
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
                return deals
        return ()

    def scan(self, query: str) -> list[LiveScanResult]:
        amazon_listings = list(self.amazon.search(query))
        results: list[LiveScanResult] = []
        for listing in amazon_listings:
            deals = self._scan_ebay_candidates(listing)
            if deals:
                results.append(LiveScanResult(listing.product, listing.offer, deals))
        return results
