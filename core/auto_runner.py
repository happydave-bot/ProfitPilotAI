from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable, Iterable

from core.alert_monitor import AlertMonitor
from core.deal_scanner import ScanCandidate
from core.notifiers import Notifier

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RunnerConfig:
    interval_seconds: float = 900.0


class AutoRunner:
    """Run a scan repeatedly, alerting only on newly discovered deals."""

    def __init__(
        self,
        scan: Callable[[], Iterable[ScanCandidate]],
        notifier: Notifier,
        monitor: AlertMonitor | None = None,
        config: RunnerConfig | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.scan = scan
        self.notifier = notifier
        self.monitor = monitor or AlertMonitor()
        self.config = config or RunnerConfig()
        self.sleep = sleep
        if self.config.interval_seconds <= 0:
            raise ValueError("interval_seconds muss größer als 0 sein")

    def run_once(self) -> list[ScanCandidate]:
        candidates = list(self.scan())
        fresh = self.monitor.check(candidates)
        for candidate in fresh:
            try:
                self.notifier.send(self._message(candidate))
            except Exception:
                logger.exception("Benachrichtigung konnte nicht gesendet werden")
        return fresh

    def run(self, max_cycles: int | None = None) -> int:
        cycles = 0
        while max_cycles is None or cycles < max_cycles:
            self.run_once()
            cycles += 1
            if max_cycles is None or cycles < max_cycles:
                self.sleep(self.config.interval_seconds)
        return cycles

    @staticmethod
    def _message(candidate: ScanCandidate) -> str:
        return (
            f"🚨 TOP DEAL: {candidate.product.title}\n"
            f"Einkauf: {candidate.amazon.price:.2f} € | Verkauf: {candidate.ebay.price:.2f} €\n"
            f"Gewinn: {candidate.deal.profit:.2f} € | ROI: {candidate.deal.roi:.1f}%\n"
            f"Match: {candidate.match_confidence:.1f}%\n"
            f"Kaufen: {candidate.ebay.url}"
        )
