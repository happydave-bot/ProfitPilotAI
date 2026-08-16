from __future__ import annotations

import os
from dataclasses import dataclass
from urllib import parse, request


class NotificationError(RuntimeError):
    pass


class Notifier:
    def send(self, message: str) -> None:
        raise NotImplementedError


@dataclass(slots=True)
class MemoryNotifier(Notifier):
    messages: list[str]

    def __init__(self) -> None:
        self.messages = []

    def send(self, message: str) -> None:
        self.messages.append(message)


class TelegramNotifier(Notifier):
    """Telegram sender using only environment variables for credentials."""

    def __init__(self, token: str | None = None, chat_id: str | None = None, timeout: float = 10.0) -> None:
        self.token = token or os.getenv("PROFITPILOT_TELEGRAM_TOKEN")
        self.chat_id = chat_id or os.getenv("PROFITPILOT_TELEGRAM_CHAT_ID")
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def send(self, message: str) -> None:
        if not self.configured:
            raise NotificationError("Telegram ist nicht konfiguriert")

        payload = parse.urlencode({"chat_id": self.chat_id, "text": message}).encode()
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            with request.urlopen(request.Request(url, data=payload, method="POST"), timeout=self.timeout) as response:
                if response.status != 200:
                    raise NotificationError(f"Telegram HTTP {response.status}")
        except Exception as exc:
            if isinstance(exc, NotificationError):
                raise
            raise NotificationError(f"Telegram-Versand fehlgeschlagen: {exc}") from exc
