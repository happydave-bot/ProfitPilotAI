from __future__ import annotations

import logging
import os

from core.alert_monitor import AlertMonitor
from core.auto_runner import AutoRunner, RunnerConfig
from core.notifiers import TelegramNotifier
from core.state_store import JsonStateStore


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


def build_live_runner() -> AutoRunner | None:
    """Build the live runner when Telegram credentials are configured."""
    notifier = TelegramNotifier()
    if not notifier.configured:
        return None

    interval = float(os.getenv("PROFITPILOT_INTERVAL_SECONDS", "900"))
    state_path = os.getenv("PROFITPILOT_STATE_FILE", "data/alert_state.json")
    store = JsonStateStore(state_path)
    monitor = AlertMonitor()
    monitor.seen.update(store.load())

    def scan():
        # BUILD 015 keeps the live entry point provider-agnostic.
        # Replace this function with the configured Amazon/eBay live pipeline.
        return []

    return AutoRunner(
        scan,
        notifier,
        monitor=monitor,
        config=RunnerConfig(interval_seconds=interval),
    )


def main() -> None:
    runner = build_live_runner()
    if runner is None:
        raise SystemExit(
            "Telegram ist nicht konfiguriert. Setze PROFITPILOT_TELEGRAM_TOKEN "
            "und PROFITPILOT_TELEGRAM_CHAT_ID."
        )

    try:
        runner.run()
    finally:
        # The monitor is persisted through its configured state store on shutdown.
        # Rebuild the same store path so the entry point remains simple and testable.
        state_path = os.getenv("PROFITPILOT_STATE_FILE", "data/alert_state.json")
        JsonStateStore(state_path).save(runner.monitor.seen)


if __name__ == "__main__":
    main()
