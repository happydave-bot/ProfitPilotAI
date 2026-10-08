from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass
from urllib import error, parse, request


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

    def __init__(self, token: str | None = None, chat_id: str | None = None, timeout: float = 10.0, max_retries: int = 2, sleep=time.sleep) -> None:
        self.token = token or os.getenv("PROFITPILOT_TELEGRAM_TOKEN")
        self.chat_id = chat_id or os.getenv("PROFITPILOT_TELEGRAM_CHAT_ID")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Telegram timeout muss endlich und größer als 0 sein")
        if isinstance(max_retries, bool) or not isinstance(max_retries, int) or max_retries < 0 or max_retries > 2:
            raise ValueError("Telegram max retries muss ein Integer zwischen 0 und 2 sein")
        self.timeout = timeout
        self.max_retries = max_retries
        self.sleep = sleep

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
        for attempt in range(self.max_retries + 1):
            try:
                with request.urlopen(request.Request(url, data=payload, method="POST"), timeout=self.timeout) as response:
                    if response.status != 200:
                        body = self._decode_response(response.read())
                        if response.status in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                            self.sleep(self._retry_delay(response.status, body, attempt))
                            continue
                        raise NotificationError(f"Telegram HTTP {response.status}")
                    body = self._decode_response(response.read())
                    if body.get("ok") is not True:
                        raise NotificationError("Telegram hat den Versand abgelehnt")
                    return
            except error.HTTPError as exc:
                body = self._decode_response(exc.read())
                if exc.code in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                    self.sleep(self._retry_delay(exc.code, body, attempt))
                    continue
                raise NotificationError(f"Telegram HTTP {exc.code}") from exc
            except Exception as exc:
                if isinstance(exc, NotificationError):
                    raise
                raise NotificationError(f"Telegram-Versand fehlgeschlagen: {exc}") from exc

    @staticmethod
    def _decode_response(raw: bytes) -> dict:
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise NotificationError("Ungültige Telegram-Antwort") from exc
        if not isinstance(body, dict):
            raise NotificationError("Ungültige Telegram-Antwort")
        return body

    @staticmethod
    def _retry_delay(status: int, body: dict, attempt: int) -> float:
        if status == 429:
            parameters = body.get("parameters")
            retry_after = parameters.get("retry_after") if isinstance(parameters, dict) else None
            if isinstance(retry_after, int) and not isinstance(retry_after, bool) and retry_after >= 0:
                return min(float(retry_after), 5.0)
        return min(0.5 * (2**attempt), 5.0)
