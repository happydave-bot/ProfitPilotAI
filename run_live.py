from __future__ import annotations

import argparse
import logging
import math
import os

from dotenv import load_dotenv

load_dotenv()

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
        logging.info("DRY RUN - würde senden:
%s", message)


def _read_queries() -> list[str]:
    raw = os.getenv("PROFITPILOT_QUERIES", "")
    if raw.strip():
        return [item.strip() for item in raw.split(",") if item.strip()]
    single = os.getenv("PROFITPILOT_QUERY", "").strip()
    return [single] if single else []


def _read_float_env(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} muss eine Zahl sein") from exc
    if not math.isfinite(value):
        raise ValueError(f"{name} muss endlich sein")
    return value


def _read_int_env(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} muss eine ganze Zahl sein") from exc


def build_live_runner(dry_run: bool = False) -> AutoRunner | None:
    notifier: Notifier = DryRunNotifier() if dry_run else TelegramNotifier()
    if not notifier.configured:
        return None
    amazon_config = AmazonCreatorsConfig.from_env()
    ebay_config = EbayBrowseConfig.from_env()
    queries = _read_queries()
    ebay_only = os.getenv("PROFITPILOT_EBAY_ONLY", "").lower() in {"1", "true", "yes"}
    if ebay_config is None or not queries:
        return None
    if amazon_config is None and not ebay_only:
        return None

    try:
        fee_percent = _read_float_env("PROFITPILOT_EBAY_FEE_PERCENT", 12.9)
        packaging_cost = _read_float_env("PROFITPILOT_PACKAGING_COST", 2.0)
        max_ebay_results = _read_int_env("PROFITPILOT_MAX_EBAY_RESULTS", 20)
        interval = _read_float_env("PROFITPILOT_INTERVAL_SECONDS", 900)
        service_config = LiveDealConfig(
            ebay_fee_percent=fee_percent,
            packaging_cost=packaging_cost,
            max_ebay_results=max_ebay_results,
        )
        runner_config = RunnerConfig(interval_seconds=interval)
    except ValueError as exc:
        logging.error("LIVE KONFIGURATION FEHLER | %s", exc)
        return None

    amazon = AmazonCreatorsConnector(amazon_config) if amazon_config is not None else None
    ebay = EbayBrowseConnector(ebay_config)
    service = LiveDealService(amazon, ebay, service_config)

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
        config=runner_config,
        state_store=store,
    )


def run_ebay_connectivity_test() -> int:
    """Perform one real eBay Browse API search without Telegram or state changes."""
    config = EbayBrowseConfig.from_env()
    queries = _read_queries()
    if config is None:
        print("eBay-Test: EBAY_CLIENT_ID/EBAY_CLIENT_SECRET fehlen")
        return 2
    if not queries:
        print("eBay-Test: PROFITPILOT_QUERY oder PROFITPILOT_QUERIES fehlt")
        return 2

    connector = EbayBrowseConnector(config)
    for query in queries:
        print(f"eBay-Test: Suche '{query}' ...")
        try:
            results = connector.search(query)
        except Exception as exc:
            print(f"eBay-Test: FEHLER: {exc}")
            return 1
        print(f"eBay-Test: OK - {len(results)} Angebote gefunden")
        for listing in results[:5]:
            print(f"  - {listing.product.title} | {listing.offer.price:.2f} EUR | {listing.offer.url}")
    return 0


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
    parser.add_argument(
        "--test-ebay",
        action="store_true",
        help="eine echte eBay-Browse-Suche testen; kein Telegram und keine Zustandsänderung",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.check:
        check_dry_run = args.dry_run or os.getenv("PROFITPILOT_DRY_RUN", "").lower() in {"1", "true", "yes"}
        result = validate_live_environment(dry_run=check_dry_run)
        print(result.summary())
        raise SystemExit(0 if result.ok else 2)

    if args.test_ebay:
        raise SystemExit(run_ebay_connectivity_test())

    dry_run = args.dry_run or os.getenv("PROFITPILOT_DRY_RUN", "").lower() in {"1", "true", "yes"}
    runner = build_live_runner(dry_run=dry_run)
    if runner is None:
        raise SystemExit(
            "Live-Betrieb nicht konfiguriert oder ungültig. Benötigt Amazon-, eBay-Zugangsdaten "
            "und PROFITPILOT_QUERY/PROFITPILOT_QUERIES. Für normalen Betrieb zusätzlich Telegram."
        )

    try:
        runner.run(max_cycles=1 if args.once else None)
    finally:
        state_path = os.getenv("PROFITPILOT_STATE_FILE", "data/alert_state.json")
        JsonStateStore(state_path).save(runner.monitor.seen)


if __name__ == "__main__":
    main()
