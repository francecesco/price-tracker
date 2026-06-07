import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)

from scraper import fetch_product_info


def _names_match(stored: str, current: str) -> bool:
    """Ritorna False se i nomi sono troppo diversi (meno del 50% di parole in comune)."""
    words_stored = set(stored.lower().split())
    words_current = set(current.lower().split())
    if not words_stored or not words_current:
        return True
    overlap = len(words_stored & words_current) / min(len(words_stored), len(words_current))
    return overlap >= 0.5



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
        info = fetch_product_info(product.url)
        await asyncio.sleep(random.uniform(1.0, 3.0))
        if info is None or info["price"] is None:
            continue

        # Controllo sicurezza: il prodotto al link è cambiato?
        if info["name"] != "Prodotto senza nome" and not _names_match(product.name, info["name"]):
            await send_alert(
                f"⚠️ *Prodotto cambiato?*\n"
                f"ID `{product.id}` — il nome non corrisponde più:\n"
                f"*Era:* {product.name}\n"
                f"*Ora:* {info['name']}\n"
                f"[Verifica il link]({product.url})"
            )

        price = info["price"]
        previous_price = product.current_price
        update_product_price(db_path, product.id, price)

        if product.target_price and should_send_alert(
            price, product.target_price,
            product.last_alert_at, previous_price,
        ):
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            msg = (
                f"🔔 Prezzo raggiunto!\n"
                f"*{product.name}*\n"
                f"💰 Prezzo attuale: €{price:.2f}\n"
                f"🎯 Il tuo target: €{product.target_price:.2f}"
            )
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🛒 Acquista ora", url=product.url)
            ]])
            await send_alert(msg, reply_markup=keyboard)
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
    check_interval_minutes: int,
    report_day: str,
    report_time: str,
    price_check_job: Callable,
    weekly_report_job: Callable,
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(price_check_job, "interval", minutes=check_interval_minutes, id="price_check")
    hour, minute = map(int, report_time.split(":"))
    scheduler.add_job(
        weekly_report_job, "cron",
        day_of_week=_DAY_MAP.get(report_day.lower(), "fri"),
        hour=hour, minute=minute,
        id="weekly_report",
    )
    return scheduler
