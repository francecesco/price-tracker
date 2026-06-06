import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    telegram_token: str
    telegram_chat_id: int
    wishlist_url: str
    check_interval_minutes: int
    report_day: str
    report_time: str
    db_path: str

def load_config() -> Config:
    return Config(
        telegram_token=os.environ["TELEGRAM_BOT_TOKEN"],
        telegram_chat_id=int(os.environ["TELEGRAM_CHAT_ID"]),
        wishlist_url=os.environ["AMAZON_WISHLIST_URL"],
        check_interval_minutes=int(os.environ.get("CHECK_INTERVAL_MINUTES", "30")),
        report_day=os.environ.get("REPORT_DAY", "friday"),
        report_time=os.environ.get("REPORT_TIME", "19:00"),
        db_path=os.environ.get("DB_PATH", "/app/data/tracker.db"),
    )
