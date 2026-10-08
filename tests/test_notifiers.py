import pytest

from core.notifiers import MemoryNotifier, NotificationError, TelegramNotifier


def test_memory_notifier_stores_messages():
    notifier = MemoryNotifier()
    notifier.send("🚨 TOP DEAL")
    assert notifier.messages == ["🚨 TOP DEAL"]


def test_telegram_requires_configuration():
    notifier = TelegramNotifier(token="", chat_id="")
    assert not notifier.configured
    with pytest.raises(NotificationError, match="nicht konfiguriert"):
        notifier.send("test")


def test_telegram_uses_explicit_configuration_without_network_call(monkeypatch):
    notifier = TelegramNotifier(token="secret", chat_id="123")
    assert notifier.configured
    assert notifier.token == "secret"
    assert notifier.chat_id == "123"


def test_telegram_rejects_invalid_timeout():
    for value in (0, -1, float("inf"), float("nan")):
        with pytest.raises(ValueError, match="endlich und größer als 0"):
            TelegramNotifier(token="secret", chat_id="123", timeout=value)


def test_telegram_rejects_empty_message(monkeypatch):
    notifier = TelegramNotifier(token="secret", chat_id="123")
    with pytest.raises(NotificationError, match="nicht leer"):
        notifier.send("")


def test_telegram_rejects_message_over_4096_characters(monkeypatch):
    notifier = TelegramNotifier(token="secret", chat_id="123")
    with pytest.raises(NotificationError, match="4096"):
        notifier.send("x" * 4097)


def test_telegram_rejects_api_error_response(monkeypatch):
    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"ok": false, "description": "Bad Request"}'

    def fake_urlopen(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr("core.notifiers.request.urlopen", fake_urlopen)
    notifier = TelegramNotifier(token="secret", chat_id="123")

    with pytest.raises(NotificationError, match="abgelehnt"):
        notifier.send("test")


@pytest.mark.parametrize("payload", [b"[]", b"null", b'"text"'])
def test_telegram_rejects_non_object_json_response(monkeypatch, payload):
    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return payload

    def fake_urlopen(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr("core.notifiers.request.urlopen", fake_urlopen)
    notifier = TelegramNotifier(token="secret", chat_id="123")

    with pytest.raises(NotificationError, match="Ungültige Telegram-Antwort"):
        notifier.send("test")


def test_telegram_accepts_success_response(monkeypatch):
    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"ok": true, "result": {"message_id": 1}}'

    def fake_urlopen(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr("core.notifiers.request.urlopen", fake_urlopen)
    notifier = TelegramNotifier(token="secret", chat_id="123")

    notifier.send("test")
