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
