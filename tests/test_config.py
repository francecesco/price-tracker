import pytest
import os


def test_load_config_reads_required_env_vars(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token-abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456789")
    monkeypatch.setenv("AMAZON_WISHLIST_URL", "https://www.amazon.it/hz/wishlist/ls/TESTLIST")
    monkeypatch.delenv("CHECK_INTERVAL_MINUTES", raising=False)
    monkeypatch.delenv("REPORT_DAY", raising=False)
    monkeypatch.delenv("REPORT_TIME", raising=False)
    monkeypatch.delenv("DB_PATH", raising=False)

    from config import load_config
    c = load_config()

    assert c.telegram_token == "test-token-abc"
    assert c.telegram_chat_id == 123456789
    assert c.wishlist_url == "https://www.amazon.it/hz/wishlist/ls/TESTLIST"
    assert c.check_interval_minutes == 30
    assert c.report_day == "friday"
    assert c.report_time == "19:00"
    assert c.db_path == "/app/data/tracker.db"


def test_load_config_custom_optional_values(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "999")
    monkeypatch.setenv("AMAZON_WISHLIST_URL", "https://www.amazon.it/hz/wishlist/ls/X")
    monkeypatch.setenv("CHECK_INTERVAL_MINUTES", "60")
    monkeypatch.setenv("REPORT_DAY", "monday")
    monkeypatch.setenv("REPORT_TIME", "09:00")
    monkeypatch.setenv("DB_PATH", "/tmp/custom.db")

    from config import load_config
    c = load_config()

    assert c.check_interval_minutes == 60
    assert c.report_day == "monday"
    assert c.report_time == "09:00"
    assert c.db_path == "/tmp/custom.db"


def test_load_config_missing_token_raises(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    monkeypatch.setenv("AMAZON_WISHLIST_URL", "https://www.amazon.it/hz/wishlist/ls/X")

    from config import load_config
    with pytest.raises(KeyError):
        load_config()


def test_load_config_missing_chat_id_raises(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setenv("AMAZON_WISHLIST_URL", "https://www.amazon.it/hz/wishlist/ls/X")

    from config import load_config
    with pytest.raises(KeyError):
        load_config()


def test_load_config_chat_id_is_int(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    monkeypatch.setenv("AMAZON_WISHLIST_URL", "https://www.amazon.it/hz/wishlist/ls/X")

    from config import load_config
    c = load_config()
    assert isinstance(c.telegram_chat_id, int)
    assert c.telegram_chat_id == 42
