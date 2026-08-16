from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from connectors.market_data import MarketDataConnector
from core.deal_scanner import DealScanner, ScanCandidate
from core.models import MarketOffer, Product


@dataclass(frozen=True, slots=True)
class PipelineResult:
    query: str
    candidates: tuple[ScanCandidate, ...]


class DealPipeline:
    """End-to-end orchestration from market search to ranked deal candidates."""

    def __init__(self, amazon: MarketDataConnector, ebay: MarketDataConnector) -> None:
        self.amazon = amazon
        self.ebay = ebay

    def run(
        self,
        query: str,
        ebay_fee_percent: float,
        packaging_cost: float = 0.0,
        limit: int | None = None,
    ) -> PipelineResult:
        amazon_listings = list(self.amazon.search(query))
        candidates: list[ScanCandidate] = []

        for amazon_listing in amazon_listings:
            ebay_listings = list(self.ebay.search(query))
            candidates.extend(
                DealScanner.scan(
                    product=amazon_listing.product,
                    amazon=amazon_listing.offer,
                    ebay_candidates=((item.product, item.offer) for item in ebay_listings),
                    ebay_fee_percent=ebay_fee_percent,
                    packaging_cost=packaging_cost,
                )
            )

        candidates.sort(key=lambda item: item.deal.profit, reverse=True)
        if limit is not None:
            candidates = candidates[: max(0, limit)]
        return PipelineResult(query=query, candidates=tuple(candidates))
