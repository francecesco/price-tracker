from datetime import datetime, timedelta
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)

try:
    from scraper import fetch_current_price
except ImportError:
    fetch_current_price = None  # type: ignore[assignment]



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


from apscheduler.schedulers.asyncio import AsyncIOScheduler


async def run_price_check(db_path: str, send_alert: Callable) -> int:
    from database import get_all_products, update_product_price, update_last_alert

    products = get_all_products(db_path)
    if not products:
        return 0

    alerts_sent = 0
    for product in products:
        price = fetch_current_price(product.url)
        if price is None:
            continue

        previous_price = product.current_price
        update_product_price(db_path, product.id, price)

        if product.target_price and should_send_alert(
            price, product.target_price,
            product.last_alert_at, previous_price,
        ):
            msg = (
                f"🔔 Prezzo raggiunto!\n"
                f"*{product.name}*\n"
                f"💰 Prezzo attuale: €{price:.2f}\n"
                f"🎯 Il tuo target: €{product.target_price:.2f}\n"
                f"🔗 [Acquista ora]({product.url})"
            )
            await send_alert(msg)
            update_last_alert(db_path, product.id)
            alerts_sent += 1

    logger.info("Price check completato: %d alert inviati", alerts_sent)
    return alerts_sent


async def run_weekly_report(db_path: str, send_message: Callable) -> None:
    from database import get_all_products

    products = get_all_products(db_path)
    if not products:
        await send_message("Nessun prodotto in tracciamento.")
        return

    lines = ["📊 *Report settimanale prezzi*\n─────────────────────────"]
    for p in products:
        price_str = f"€{p.current_price:.2f}" if p.current_price else "N/D"
        target_str = f"/ target €{p.target_price:.2f}" if p.target_price else ""
        icon = (
            "✅"
            if (p.current_price and p.target_price and p.current_price <= p.target_price)
            else "❌"
        )
        lines.append(f"{icon} {p.name[:35]} {price_str} {target_str}")

    await send_message("\n".join(lines))


_DAY_MAP = {
    "monday": "mon", "tuesday": "tue", "wednesday": "wed",
    "thursday": "thu", "friday": "fri", "saturday": "sat", "sunday": "sun",
}


def create_scheduler(
    check_interval_hours: int,
    report_day: str,
    report_time: str,
    price_check_job: Callable,
    weekly_report_job: Callable,
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(price_check_job, "interval", hours=check_interval_hours, id="price_check")
    hour, minute = map(int, report_time.split(":"))
    scheduler.add_job(
        weekly_report_job, "cron",
        day_of_week=_DAY_MAP.get(report_day.lower(), "fri"),
        hour=hour, minute=minute,
        id="weekly_report",
    )
    return scheduler
