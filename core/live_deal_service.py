from __future__ import annotations

from dataclasses import dataclass
import logging
import math

from connectors.market_data import MarketListing
from core.deal_scanner import DealScanner, ScanCandidate
from core.models import MarketOffer

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class LiveDealConfig:
    ebay_fee_percent: float = 12.9
    packaging_cost: float = 2.0
    max_ebay_results: int = 20

    def __post_init__(self) -> None:
        if not math.isfinite(self.ebay_fee_percent) or not 0 <= self.ebay_fee_percent <= 100:
            raise ValueError("eBay fee percent must be between 0 and 100")
        if not math.isfinite(self.packaging_cost) or self.packaging_cost < 0:
            raise ValueError("Packaging cost must be finite and non-negative")
        if self.max_ebay_results <= 0:
            raise ValueError("Maximum eBay results must be greater than zero")


class LiveDealService:
    """Turn a product query into real cross-market deal candidates."""

    def __init__(self, amazon_connector, ebay_connector, config: LiveDealConfig | None = None):
        self.amazon = amazon_connector
        self.ebay = ebay_connector
        self.config = config or LiveDealConfig()

    @property
    def amazon_configured(self) -> bool:
        return self.amazon is not None

    @staticmethod
    def _ebay_queries(product) -> tuple[str, ...]:
        values = [product.ean, product.model, product.title]
        queries: list[str] = []
        for value in values:
            normalized = str(value or "").strip()
            if normalized and normalized not in queries:
                queries.append(normalized)
        return tuple(queries)

    def _scan_ebay_candidates(self, listing: MarketListing) -> list[ScanCandidate]:
        for ebay_query in self._ebay_queries(listing.product):
            try:
                ebay_listings = list(self.ebay.search(ebay_query))[: self.config.max_ebay_results]
            except Exception:
                logger.exception("eBay-Suche fehlgeschlagen | Query=%s", ebay_query)
                continue

            ebay_candidates = [(item.product, item.offer) for item in ebay_listings]
            deals = DealScanner.scan(
                listing.product,
                listing.offer,
                ebay_candidates,
                ebay_fee_percent=self.config.ebay_fee_percent,
                packaging_cost=self.config.packaging_cost,
            )
            if deals:
                return deals
        return []

    def scan(self, query: str) -> list[ScanCandidate]:
        query = query.strip()
        if not query or self.amazon is None:
            return []

        try:
            amazon_listings = list(self.amazon.search(query))
        except Exception:
            logger.exception("Amazon-Suche fehlgeschlagen | Query=%s", query)
            return []

        candidates: list[ScanCandidate] = []
        for listing in amazon_listings:
            candidates.extend(self._scan_ebay_candidates(listing))
        return sorted(candidates, key=lambda item: (item.deal.profit, item.deal.roi), reverse=True)
