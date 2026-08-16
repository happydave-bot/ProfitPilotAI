from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from core.deal_scanner import ScanCandidate


@dataclass(frozen=True, slots=True)
class AlertConfig:
    min_profit: float = 20.0
    min_roi: float = 40.0
    min_match_confidence: float = 99.0
    max_alerts: int = 5


class DealAlertFormatter:
    @staticmethod
    def format(candidate: ScanCandidate) -> str:
        deal = candidate.deal
        return (
            "🚨 TOP DEAL\n"
            f"{candidate.product.title}\n"
            f"Einkauf: {candidate.amazon.price:.2f} €\n"
            f"Verkauf: {candidate.ebay.price:.2f} €\n"
            f"Gewinn: {deal.profit:.2f} €\n"
            f"ROI: {deal.roi:.1f} %\n"
            f"Match: {candidate.match_confidence:.1f} %\n"
            f"Entscheidung: {deal.decision.value}"
        )


class DealAlertEngine:
    """Select only high-quality deals that are worth notifying about."""

    @staticmethod
    def select(candidates: Iterable[ScanCandidate], config: AlertConfig | None = None) -> list[ScanCandidate]:
        config = config or AlertConfig()
        selected = [
            candidate
            for candidate in candidates
            if candidate.deal.profit >= config.min_profit
            and candidate.deal.roi >= config.min_roi
            and candidate.match_confidence >= config.min_match_confidence
            and candidate.deal.decision.value == "KAUFEN"
        ]
        selected.sort(key=lambda item: (item.deal.profit, item.deal.roi), reverse=True)
        return selected[: max(0, config.max_alerts)]

    @staticmethod
    def format_all(candidates: Iterable[ScanCandidate], config: AlertConfig | None = None) -> list[str]:
        return [DealAlertFormatter.format(candidate) for candidate in DealAlertEngine.select(candidates, config)]
