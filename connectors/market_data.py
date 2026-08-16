from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable

from core.models import MarketOffer, Product


@dataclass(frozen=True, slots=True)
class MarketListing:
    product: Product
    offer: MarketOffer


class MarketDataConnector(ABC):
    source: str

    @abstractmethod
    def search(self, query: str) -> Iterable[MarketListing]:
        raise NotImplementedError


class InMemoryConnector(MarketDataConnector):
    """Deterministic connector used for local development and tests."""

    source = "memory"

    def __init__(self, listings: Iterable[MarketListing] = ()) -> None:
        self._listings = tuple(listings)

    def search(self, query: str) -> list[MarketListing]:
        needle = query.casefold().strip()
        if not needle:
            return list(self._listings)
        return [
            item
            for item in self._listings
            if needle in item.product.title.casefold()
            or needle in item.product.brand.casefold()
            or (item.product.ean and needle == item.product.ean.casefold())
            or (item.product.asin and needle == item.product.asin.casefold())
        ]
