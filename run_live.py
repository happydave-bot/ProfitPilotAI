from __future__ import annotations

import argparse
import logging
import os

from connectors.amazon_creators import AmazonCreatorsConfig, AmazonCreatorsConnector
from connectors.ebay_browse import EbayBrowseConfig, EbayBrowseConnector
from core.alert_monitor import AlertMonitor
from core.auto_runner import AutoRunner, RunnerConfig
from core.live_deal_service import LiveDealConfig, LiveDealService
from core.live_preflight import validate_live_environment
from core.notifiers import Notifier, TelegramNotifier
from core.state_store import JsonStateStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


class DryRunNotifier:
    """Notifier used for a safe one-cycle live connectivity test."""

    configured = True

    def __init__(self) -> None:
        self.messages: list[str] = []

    def send(self, message: str) -> None:
        self.messages.append(message)
        logging.info("DRY RUN - würde senden:\n%s", message)


def _read_queries() -> list[str]:
    raw = os.getenv("PROFITPILOT_QUERIES", "")
    if raw.strip():
        return [item.strip() for item in raw.split(",") if item.strip()]
    single = os.getenv("PROFITPILOT_QUERY", "").strip()
    return [single] if single else []


def build_live_runner(dry_run: bool = False) -> AutoRunner | None:
    notifier: Notifier = DryRunNotifier() if dry_run else TelegramNotifier()
    if not notifier.configured:
        return None
    amazon_config = AmazonCreatorsConfig.from_env()
    ebay_config = EbayBrowseConfig.from_env()
    queries = _read_queries()
    if amazon_config is None or ebay_config is None or not queries:
        return None

    amazon = AmazonCreatorsConnector(amazon_config)
    ebay = EbayBrowseConnector(ebay_config)
    service = LiveDealService(
        amazon,
        ebay,
        LiveDealConfig(
            ebay_fee_percent=float(os.getenv("PROFITPILOT_EBAY_FEE_PERCENT", "12.9")),
            packaging_cost=float(os.getenv("PROFITPILOT_PACKAGING_COST", "2.0")),
            max_ebay_results=max(1, int(os.getenv("PROFITPILOT_MAX_EBAY_RESULTS", "20"))),
        ),
    )

    interval = float(os.getenv("PROFITPILOT_INTERVAL_SECONDS", "900"))
    state_path = os.getenv("PROFITPILOT_STATE_FILE", "data/alert_state.json")
    store = JsonStateStore(state_path)
    monitor = AlertMonitor()
    monitor.seen.update(store.load())

    def scan():
        results = []
        for query in queries:
            logging.info("LIVE SCAN | %s", query)
            found = service.scan(query)
            logging.info("LIVE RESULT | %s | %d profitable matches", query, len(found))
            results.extend(found)
        return sorted(results, key=lambda item: (item.deal.profit, item.deal.roi), reverse=True)

    return AutoRunner(
        scan,
        notifier,
        monitor=monitor,
        config=RunnerConfig(interval_seconds=interval),
        state_store=store,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ProfitPilotAI Live Runner")
    parser.add_argument(
        "--once",
        action="store_true",
        help="genau einen Scan durchführen und danach beenden",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="einen sicheren Test ohne Telegram-Versand durchführen",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="nur Konfiguration prüfen; keine Netzwerk- oder Telegram-Anfragen",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.check:
        result = validate_live_environment()
        print(result.summary())
        raise SystemExit(0 if result.ok else 2)

    dry_run = args.dry_run or os.getenv("PROFITPILOT_DRY_RUN", "").lower() in {"1", "true", "yes"}
    runner = build_live_runner(dry_run=dry_run)
    if runner is None:
        raise SystemExit(
            "Live-Betrieb nicht konfiguriert. Benötigt Amazon-, eBay-Zugangsdaten "
            "und PROFITPILOT_QUERY/PROFITPILOT_QUERIES. Für normalen Betrieb zusätzlich Telegram."
        )

    try:
        runner.run(max_cycles=1 if args.once else None)
    finally:
        state_path = os.getenv("PROFITPILOT_STATE_FILE", "data/alert_state.json")
        JsonStateStore(state_path).save(runner.monitor.seen)


if __name__ == "__main__":
    main()
