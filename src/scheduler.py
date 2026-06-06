from datetime import datetime, timedelta
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


def should_send_alert(
    current_price: float,
    target_price: float,
    last_alert_at: Optional[str],
    previous_price: Optional[float],
) -> bool:
    if current_price > target_price:
        return False
    if previous_price is not None and current_price != previous_price:
        return True
    if last_alert_at is None:
        return True
    last = datetime.fromisoformat(last_alert_at)
    return (datetime.utcnow() - last) >= timedelta(hours=24)
