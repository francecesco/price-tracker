import logging
import os
from telegram.ext import Application
from config import load_config
from database import init_db
from bot import build_application
from scheduler import create_scheduler, run_price_check, run_weekly_report

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    config = load_config()
    os.makedirs(os.path.dirname(config.db_path), exist_ok=True)
    init_db(config.db_path)
    logger.info("Database inizializzato: %s", config.db_path)

    async def post_init(app: Application) -> None:
        async def send_message(msg: str, reply_markup=None) -> None:
            await app.bot.send_message(
                config.telegram_chat_id, msg,
                parse_mode="Markdown",
                reply_markup=reply_markup,
            )

        async def price_check_job() -> None:
            count = await run_price_check(config.db_path, send_message)
            logger.info("Price check: %d alert inviati", count)

        async def weekly_report_job() -> None:
            await run_weekly_report(config.db_path, send_message)

        scheduler = create_scheduler(
            config.check_interval_minutes,
            config.report_day,
            config.report_time,
            price_check_job,
            weekly_report_job,
        )
        app.bot_data["run_price_check"] = price_check_job
        app.bot_data["scheduler"] = scheduler
        scheduler.start()
        logger.info(
            "Scheduler avviato: check ogni %dmin, report %s alle %s",
            config.check_interval_minutes, config.report_day, config.report_time,
        )

    app = build_application(
        config.telegram_token,
        {
            "chat_id": config.telegram_chat_id,
            "db_path": config.db_path,
            "wishlist_url": config.wishlist_url,
        },
        post_init=post_init,
    )

    logger.info("Bot avviato. In ascolto...")
    app.run_polling()


if __name__ == "__main__":
    main()
