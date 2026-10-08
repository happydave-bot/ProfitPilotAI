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
        if isinstance(self.max_ebay_results, bool) or not isinstance(self.max_ebay_results, int):
            raise ValueError("Maximum eBay results must be an integer")
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

    @property
    def ebay_configured(self) -> bool:
        return self.ebay is not None

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
        if not self.ebay_configured:
            return []

        for ebay_query in self._ebay_queries(listing.product):
            try:
                raw_ebay_listings = list(self.ebay.search(ebay_query))
                unique_ebay_listings: list[MarketListing] = []
                seen_offer_urls: set[str] = set()
                for ebay_listing in raw_ebay_listings:
                    offer_url = str(ebay_listing.offer.url or "").strip()
                    if offer_url and offer_url in seen_offer_urls:
                        continue
                    if offer_url:
                        seen_offer_urls.add(offer_url)
                    unique_ebay_listings.append(ebay_listing)
                    if len(unique_ebay_listings) >= self.config.max_ebay_results:
                        break
                ebay_listings = unique_ebay_listings
            except Exception:
                logger.exception("eBay-Suche fehlgeschlagen | Query=%s", ebay_query)
                continue

            deals: list[ScanCandidate] = []
            for index, ebay_listing in enumerate(ebay_listings):
                try:
                    ebay_candidates = [(ebay_listing.product, ebay_listing.offer)]
                    deals.extend(
                        DealScanner.scan(
                            listing.product,
                            listing.offer,
                            ebay_candidates,
                            ebay_fee_percent=self.config.ebay_fee_percent,
                            packaging_cost=self.config.packaging_cost,
                        )
                    )
                except Exception:
                    logger.exception(
                        "eBay-Listing konnte nicht verarbeitet werden | Query=%s | Index=%s",
                        ebay_query,
                        index,
                    )
                    continue

            if deals:
                return sorted(deals, key=lambda item: (item.deal.profit, item.deal.roi), reverse=True)
        return []

    def scan(self, query: str) -> list[ScanCandidate]:
        query = query.strip()
        if not query or self.amazon is None or self.ebay is None:
            return []

        try:
            amazon_listings = list(self.amazon.search(query))
        except Exception:
            logger.exception("Amazon-Suche fehlgeschlagen | Query=%s", query)
            return []

        candidates: list[ScanCandidate] = []
        for index, listing in enumerate(amazon_listings):
            try:
                candidates.extend(self._scan_ebay_candidates(listing))
            except Exception:
                logger.exception("Amazon-Listing konnte nicht verarbeitet werden | Index=%s", index)
                continue

        candidates.sort(key=lambda item: (item.deal.profit, item.deal.roi), reverse=True)
        unique_candidates: list[ScanCandidate] = []
        seen_offer_urls: set[str] = set()
        for candidate in candidates:
            offer_url = str(candidate.ebay.url or "").strip()
            if offer_url and offer_url in seen_offer_urls:
                continue
            if offer_url:
                seen_offer_urls.add(offer_url)
            unique_candidates.append(candidate)
        return unique_candidates
