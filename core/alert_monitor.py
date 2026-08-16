from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from core.alerts import AlertConfig, DealAlertEngine
from core.deal_scanner import ScanCandidate


@dataclass(slots=True)
class AlertMonitor:
    """Stateful monitor that emits each qualifying deal fingerprint once."""

    config: AlertConfig = field(default_factory=AlertConfig)
    seen: set[str] = field(default_factory=set)

    @staticmethod
    def fingerprint(candidate: ScanCandidate) -> str:
        product = candidate.product
        identifier = product.ean or product.asin or product.model or product.title.strip().lower()
        return f"{identifier}|{candidate.amazon.price:.2f}|{candidate.ebay.price:.2f}"

    def check(self, candidates: Iterable[ScanCandidate]) -> list[ScanCandidate]:
        fresh: list[ScanCandidate] = []
        for candidate in DealAlertEngine.select(candidates, self.config):
            key = self.fingerprint(candidate)
            if key not in self.seen:
                self.seen.add(key)
                fresh.append(candidate)
        return fresh

    def messages(self, candidates: Iterable[ScanCandidate]) -> list[str]:
        return [
            f"🚨 {candidate.product.title} | Gewinn {candidate.deal.profit:.2f} € | ROI {candidate.deal.roi:.1f}%"
            for candidate in self.check(candidates)
        ]

    def reset(self) -> None:
        self.seen.clear()
