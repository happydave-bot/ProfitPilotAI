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


def main() -> None:
    interval = float(os.getenv("PROFITPILOT_INTERVAL_SECONDS", "900"))
    state_path = os.getenv("PROFITPILOT_STATE_FILE", "data/alert_state.json")
    store = JsonStateStore(state_path)
    monitor = AlertMonitor()
    monitor.seen.update(store.load())

    notifier = TelegramNotifier()
    if not notifier.configured:
        raise SystemExit(
            "Telegram ist nicht konfiguriert. Setze PROFITPILOT_TELEGRAM_TOKEN "
            "und PROFITPILOT_TELEGRAM_CHAT_ID."
        )

    def scan():
        # BUILD 015 keeps the live entry point provider-agnostic.
        # Replace this function with the configured Amazon/eBay live pipeline.
        return []

    runner = AutoRunner(
        scan,
        notifier,
        monitor=monitor,
        config=RunnerConfig(interval_seconds=interval),
    )

    try:
        runner.run()
    finally:
        store.save(monitor.seen)


if __name__ == "__main__":
    main()
