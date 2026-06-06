import pytest
from datetime import datetime, timedelta
from scheduler import should_send_alert


def _ts(delta_hours: float = 0) -> str:
    return (datetime.utcnow() - timedelta(hours=delta_hours)).isoformat()


def test_no_alert_when_above_target():
    assert should_send_alert(250.0, 200.0, None, None) is False

def test_alert_when_first_time_below_target():
    assert should_send_alert(190.0, 200.0, None, None) is True

def test_alert_when_price_drops_further():
    assert should_send_alert(180.0, 200.0, _ts(1), 195.0) is True

def test_no_alert_price_unchanged_within_24h():
    assert should_send_alert(190.0, 200.0, _ts(12), 190.0) is False

def test_alert_price_unchanged_after_24h():
    assert should_send_alert(190.0, 200.0, _ts(25), 190.0) is True

def test_alert_price_at_exact_target():
    assert should_send_alert(200.0, 200.0, None, None) is True

def test_no_alert_above_target_even_with_old_alert():
    assert should_send_alert(210.0, 200.0, _ts(48), None) is False


import asyncio
from unittest.mock import AsyncMock, patch
from database import add_product, update_product_target
from scheduler import run_price_check, run_weekly_report


@pytest.mark.asyncio
async def test_run_price_check_sends_alert_when_below_target(tmp_db):
    p = add_product(tmp_db, "B09XS7JWHH", "Sony", "https://amazon.it/dp/B09XS7JWHH", 250.0, "manual")
    update_product_target(tmp_db, p.id, 220.0)
    send_alert = AsyncMock()
    with patch("scheduler.fetch_current_price", return_value=200.0):
        count = await run_price_check(tmp_db, send_alert)
    assert count == 1
    send_alert.assert_called_once()
    msg = send_alert.call_args[0][0]
    assert "Sony" in msg
    assert "200" in msg


@pytest.mark.asyncio
async def test_run_price_check_no_alert_above_target(tmp_db):
    p = add_product(tmp_db, "B09XS7JWHH", "Sony", "https://amazon.it/dp/B09XS7JWHH", 250.0, "manual")
    update_product_target(tmp_db, p.id, 180.0)
    send_alert = AsyncMock()
    with patch("scheduler.fetch_current_price", return_value=200.0):
        count = await run_price_check(tmp_db, send_alert)
    assert count == 0
    send_alert.assert_not_called()


@pytest.mark.asyncio
async def test_run_price_check_no_alert_without_target(tmp_db):
    add_product(tmp_db, "B09XS7JWHH", "Sony", "https://amazon.it/dp/B09XS7JWHH", 250.0, "manual")
    send_alert = AsyncMock()
    with patch("scheduler.fetch_current_price", return_value=100.0):
        count = await run_price_check(tmp_db, send_alert)
    assert count == 0
    send_alert.assert_not_called()


@pytest.mark.asyncio
async def test_run_weekly_report_with_products(tmp_db):
    p = add_product(tmp_db, "B09XS7JWHH", "Sony WH-1000XM5", "https://amazon.it/dp/B09XS7JWHH", 219.0, "manual")
    update_product_target(tmp_db, p.id, 220.0)
    send_message = AsyncMock()
    await run_weekly_report(tmp_db, send_message)
    send_message.assert_called_once()
    msg = send_message.call_args[0][0]
    assert "Sony" in msg
    assert "219" in msg


@pytest.mark.asyncio
async def test_run_weekly_report_empty_list(tmp_db):
    send_message = AsyncMock()
    await run_weekly_report(tmp_db, send_message)
    send_message.assert_called_once()
    assert "Nessun prodotto" in send_message.call_args[0][0]
