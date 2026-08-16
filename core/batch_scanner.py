from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Callable

from core.deal_scanner import DealScanner, ScanCandidate
from core.models import MarketOffer, Product


@dataclass(frozen=True, slots=True)
class BatchScanConfig:
    ebay_fee_percent: float = 12.9
    packaging_cost: float = 2.0
    min_profit: float = 10.0
    min_roi: float = 20.0
    max_results: int = 20


class BatchScanner:
    """Scan many source products and return one globally ranked deal list."""

    @staticmethod
    def scan(
        products: Iterable[Product],
        amazon_offer_for: Callable[[Product], MarketOffer],
        ebay_candidates_for: Callable[[Product], Iterable[tuple[Product, MarketOffer]]],
        config: BatchScanConfig | None = None,
    ) -> list[ScanCandidate]:
        config = config or BatchScanConfig()
        results: list[ScanCandidate] = []

        for product in products:
            candidates = DealScanner.scan(
                product,
                amazon_offer_for(product),
                ebay_candidates_for(product),
                ebay_fee_percent=config.ebay_fee_percent,
                packaging_cost=config.packaging_cost,
            )
            results.extend(
                candidate
                for candidate in candidates
                if candidate.deal.profit >= config.min_profit
                and candidate.deal.roi >= config.min_roi
            )

        results.sort(
            key=lambda item: (item.deal.profit, item.deal.roi, item.match_confidence),
            reverse=True,
        )
        return results[: max(0, config.max_results)]
