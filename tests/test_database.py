import pytest
from database import (
    init_db, add_product, get_product_by_asin, get_product_by_id,
    get_all_products, update_product_price, update_product_target,
    update_last_alert, remove_product
)

def test_init_db_creates_tables(tmp_db):
    import sqlite3
    with sqlite3.connect(tmp_db) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "products" in tables
    assert "price_history" in tables

def test_add_and_get_product(tmp_db):
    p = add_product(tmp_db, "B07XJ8C8F5", "Sony WH-1000XM5", "https://amazon.it/dp/B07XJ8C8F5", 219.99, "manual")
    assert p.id is not None
    assert p.asin == "B07XJ8C8F5"
    assert p.current_price == 219.99
    assert p.source == "manual"
    assert p.target_price is None

def test_get_product_by_asin(tmp_db):
    add_product(tmp_db, "B07XJ8C8F5", "Sony", "https://amazon.it/dp/B07XJ8C8F5", 100.0, "manual")
    p = get_product_by_asin(tmp_db, "B07XJ8C8F5")
    assert p is not None
    assert p.asin == "B07XJ8C8F5"

def test_get_product_by_asin_missing_returns_none(tmp_db):
    assert get_product_by_asin(tmp_db, "XXXXXXXXXX") is None

def test_asin_unique_constraint(tmp_db):
    import sqlite3
    add_product(tmp_db, "B07XJ8C8F5", "Sony", "https://amazon.it/dp/B07XJ8C8F5", 100.0, "manual")
    with pytest.raises(sqlite3.IntegrityError):
        add_product(tmp_db, "B07XJ8C8F5", "Sony Dup", "https://amazon.it/dp/B07XJ8C8F5", 90.0, "manual")

def test_update_product_price_and_history(tmp_db):
    import sqlite3
    p = add_product(tmp_db, "B07XJ8C8F5", "Sony", "https://amazon.it/dp/B07XJ8C8F5", 219.99, "manual")
    update_product_price(tmp_db, p.id, 199.99)
    updated = get_product_by_id(tmp_db, p.id)
    assert updated.current_price == 199.99
    with sqlite3.connect(tmp_db) as conn:
        rows = conn.execute("SELECT price FROM price_history WHERE product_id = ?", (p.id,)).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == 199.99

def test_update_product_target(tmp_db):
    p = add_product(tmp_db, "B07XJ8C8F5", "Sony", "https://amazon.it/dp/B07XJ8C8F5", 219.99, "manual")
    update_product_target(tmp_db, p.id, 200.0)
    updated = get_product_by_id(tmp_db, p.id)
    assert updated.target_price == 200.0

def test_remove_product(tmp_db):
    p = add_product(tmp_db, "B07XJ8C8F5", "Sony", "https://amazon.it/dp/B07XJ8C8F5", 219.99, "manual")
    assert remove_product(tmp_db, p.id) is True
    assert get_product_by_id(tmp_db, p.id) is None

def test_remove_nonexistent_product(tmp_db):
    assert remove_product(tmp_db, 9999) is False

def test_get_all_products(tmp_db):
    add_product(tmp_db, "ASIN000001", "Prod1", "https://amazon.it/dp/ASIN000001", 10.0, "manual")
    add_product(tmp_db, "ASIN000002", "Prod2", "https://amazon.it/dp/ASIN000002", 20.0, "wishlist")
    products = get_all_products(tmp_db)
    assert len(products) == 2

def test_update_last_alert(tmp_db):
    p = add_product(tmp_db, "B07XJ8C8F5", "Sony", "https://amazon.it/dp/B07XJ8C8F5", 219.99, "manual")
    assert p.last_alert_at is None
    update_last_alert(tmp_db, p.id)
    updated = get_product_by_id(tmp_db, p.id)
    assert updated.last_alert_at is not None
