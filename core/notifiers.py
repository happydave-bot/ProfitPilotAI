from __future__ import annotations

import json
import math
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
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Telegram timeout muss endlich und größer als 0 sein")
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def send(self, message: str) -> None:
        if not self.configured:
            raise NotificationError("Telegram ist nicht konfiguriert")
        if not isinstance(message, str):
            raise NotificationError("Telegram-Nachricht muss ein String sein")
        if not message:
            raise NotificationError("Telegram-Nachricht darf nicht leer sein")
        if len(message) > 4096:
            raise NotificationError("Telegram-Nachricht darf höchstens 4096 Zeichen enthalten")

        payload = parse.urlencode({"chat_id": self.chat_id, "text": message}).encode()
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            with request.urlopen(request.Request(url, data=payload, method="POST"), timeout=self.timeout) as response:
                if response.status != 200:
                    raise NotificationError(f"Telegram HTTP {response.status}")
                try:
                    body = json.loads(response.read().decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise NotificationError("Ungültige Telegram-Antwort") from exc
                if body.get("ok") is not True:
                    raise NotificationError("Telegram hat den Versand abgelehnt")
        except Exception as exc:
            if isinstance(exc, NotificationError):
                raise
            raise NotificationError(f"Telegram-Versand fehlgeschlagen: {exc}") from exc
