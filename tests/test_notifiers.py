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
