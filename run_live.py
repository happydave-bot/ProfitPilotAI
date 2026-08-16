from __future__ import annotations

import logging
import os

from connectors.amazon_creators import AmazonCreatorsConfig, AmazonCreatorsConnector
from connectors.ebay_browse import EbayBrowseConfig, EbayBrowseConnector
from core.alert_monitor import AlertMonitor
from core.auto_runner import AutoRunner, RunnerConfig
from core.live_deal_service import LiveDealConfig, LiveDealService
from core.notifiers import TelegramNotifier
from core.state_store import JsonStateStore


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


def build_live_runner() -> AutoRunner | None:
    """Build the real Amazon->eBay runner when all required credentials exist."""
    notifier = TelegramNotifier()
    if not notifier.configured:
        return None

    amazon_config = AmazonCreatorsConfig.from_env()
    ebay_config = EbayBrowseConfig.from_env()
    if amazon_config is None or ebay_config is None:
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
    query = os.getenv("PROFITPILOT_QUERY", "")

    store = JsonStateStore(state_path)
    monitor = AlertMonitor()
    monitor.seen.update(store.load())

    return AutoRunner(
        lambda: service.scan(query),
        notifier,
        monitor=monitor,
        config=RunnerConfig(interval_seconds=interval),
    )


def main() -> None:
    runner = build_live_runner()
    if runner is None:
        raise SystemExit(
            "Live-Betrieb nicht konfiguriert. Benötigt Telegram-, Amazon- und eBay-Zugangsdaten."
        )

    try:
        runner.run()
    finally:
        state_path = os.getenv("PROFITPILOT_STATE_FILE", "data/alert_state.json")
        JsonStateStore(state_path).save(runner.monitor.seen)


if __name__ == "__main__":
    main()
