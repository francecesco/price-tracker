import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Product:
    id: Optional[int]
    asin: str
    name: str
    url: str
    current_price: Optional[float]
    target_price: Optional[float]
    currency: str
    source: str
    last_alert_at: Optional[str]
    added_at: str


def init_db(db_path: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                current_price REAL,
                target_price REAL,
                currency TEXT NOT NULL DEFAULT 'EUR',
                source TEXT NOT NULL,
                last_alert_at TEXT,
                added_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                price REAL NOT NULL,
                checked_at TEXT NOT NULL
            )
        """)


def add_product(
    db_path: str,
    asin: str,
    name: str,
    url: str,
    current_price: Optional[float],
    source: str,
    target_price: Optional[float] = None,
) -> "Product":
    now = datetime.utcnow().isoformat()
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO products (asin, name, url, current_price, target_price, currency, source, added_at)
               VALUES (?, ?, ?, ?, ?, 'EUR', ?, ?)""",
            (asin, name, url, current_price, target_price, source, now),
        )
        product_id = cursor.lastrowid
        conn.commit()
    return get_product_by_id(db_path, product_id)


def get_product_by_asin(db_path: str, asin: str) -> Optional["Product"]:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT * FROM products WHERE asin = ?", (asin,)).fetchone()
        return _row_to_product(row) if row else None


def get_product_by_id(db_path: str, product_id: int) -> Optional["Product"]:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        return _row_to_product(row) if row else None


def get_all_products(db_path: str) -> list:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM products ORDER BY added_at").fetchall()
        return [_row_to_product(r) for r in rows]


def update_product_price(db_path: str, product_id: int, price: float) -> None:
    now = datetime.utcnow().isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE products SET current_price = ? WHERE id = ?", (price, product_id))
        conn.execute(
            "INSERT INTO price_history (product_id, price, checked_at) VALUES (?, ?, ?)",
            (product_id, price, now),
        )


def update_product_target(db_path: str, product_id: int, target_price: float) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE products SET target_price = ? WHERE id = ?", (target_price, product_id))


def update_last_alert(db_path: str, product_id: int) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE products SET last_alert_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), product_id),
        )


def remove_product(db_path: str, product_id: int) -> bool:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        return cursor.rowcount > 0


def _row_to_product(row) -> "Product":
    return Product(
        id=row[0], asin=row[1], name=row[2], url=row[3],
        current_price=row[4], target_price=row[5], currency=row[6],
        source=row[7], last_alert_at=row[8], added_at=row[9],
    )
