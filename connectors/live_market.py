from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from connectors.market_data import MarketListing


@dataclass(frozen=True, slots=True)
class ConnectorStatus:
    source: str
    configured: bool
    message: str


class LiveMarketConnector:
    """Adapter boundary for real marketplace APIs.

    No credentials are stored here. A fetcher supplied by the application
    performs the actual API request and returns normalized MarketListing data.
    """

    def __init__(self, source: str, fetcher: Callable[[str], Iterable[MarketListing]] | None = None):
        self.source = source
        self._fetcher = fetcher

    @property
    def status(self) -> ConnectorStatus:
        if self._fetcher is None:
            return ConnectorStatus(self.source, False, "Kein API-Fetcher konfiguriert")
        return ConnectorStatus(self.source, True, "Connector bereit")

    def search(self, query: str) -> list[MarketListing]:
        if self._fetcher is None:
            raise RuntimeError(f"{self.source}: API-Connector ist noch nicht konfiguriert")
        return list(self._fetcher(query))
