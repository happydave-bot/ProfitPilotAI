from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from core.models import DealInput, DealResult, MarketOffer, Product
from core.product_matcher import ProductMatcher
from core.profit_engine import ProfitEngine


@dataclass(frozen=True, slots=True)
class ScanCandidate:
    product: Product
    amazon: MarketOffer
    ebay: MarketOffer
    match_confidence: float
    deal: DealResult


class DealScanner:
    """Offline-first scanner that turns matched marketplace offers into deals."""

    MIN_CONFIDENCE = 95.0

    @classmethod
    def scan(
        cls,
        product: Product,
        amazon: MarketOffer,
        ebay_offers: Iterable[MarketOffer],
        ebay_fee_percent: float,
        packaging_cost: float = 0.0,
    ) -> list[ScanCandidate]:
        candidates: list[ScanCandidate] = []
        for ebay in ebay_offers:
            match = ProductMatcher.match(product, product)
            if match.confidence < cls.MIN_CONFIDENCE:
                continue
            deal = ProfitEngine.calculate(
                DealInput(
                    product=product,
                    amazon=amazon,
                    ebay=ebay,
                    ebay_fee_percent=ebay_fee_percent,
                    packaging_cost=packaging_cost,
                )
            )
            candidates.append(
                ScanCandidate(
                    product=product,
                    amazon=amazon,
                    ebay=ebay,
                    match_confidence=match.confidence,
                    deal=deal,
                )
            )
        return sorted(candidates, key=lambda item: item.deal.profit, reverse=True)
