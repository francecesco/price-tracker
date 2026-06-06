# Amazon Price Tracker — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bot Telegram self-hosted che monitora prezzi Amazon tramite Keepa API e notifica quando si raggiunge un prezzo target, deployato come singolo container Docker su CasaOS/ZimaBoard.

**Architecture:** Singolo container Python con `python-telegram-bot` v20+ (async), APScheduler per i job ricorrenti (check ogni 4h, report venerdì 19:00), SQLite per la persistenza su volume Docker montato in `./data/`.

**Tech Stack:** Python 3.11, python-telegram-bot 21.x, APScheduler 3.x, keepa 1.x, requests, beautifulsoup4, pytest, pytest-asyncio

---

## File Map

| File | Responsabilità |
|---|---|
| `src/config.py` | Legge env vars, espone dataclass `Config` |
| `src/database.py` | Init SQLite, CRUD su `products` e `price_history`, dataclass `Product` |
| `src/keepa_client.py` | Wrapper Keepa API: `get_product_info`, `get_products_info`, `extract_asin_from_url` |
| `src/scraper.py` | Scraping wishlist pubblica Amazon → lista ASIN |
| `src/scheduler.py` | `should_send_alert` (logica pura), `run_price_check`, `run_weekly_report`, `create_scheduler` |
| `src/bot.py` | Handler comandi Telegram, `build_application` |
| `src/main.py` | Entry point: wiring config + DB + bot + scheduler |
| `tests/conftest.py` | Fixture pytest: `tmp_db` (SQLite in memoria) |
| `tests/test_database.py` | Test CRUD database |
| `tests/test_keepa_client.py` | Test `extract_asin_from_url`, `_extract_current_price` |
| `tests/test_scraper.py` | Test parsing HTML wishlist |
| `tests/test_scheduler.py` | Test `should_send_alert`, `run_price_check`, `run_weekly_report` |
| `Dockerfile` | Build image Python 3.11-slim |
| `docker-compose.yml` | Definizione servizio con volume `./data` |
| `.env.example` | Template variabili d'ambiente |
| `.gitignore` | Esclude `.env`, `data/`, `__pycache__` |
| `requirements.txt` | Dipendenze con versioni fisse |

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `tests/conftest.py`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Crea requirements.txt**

```
python-telegram-bot==21.3
APScheduler==3.10.4
keepa==1.3.10
requests==2.32.3
beautifulsoup4==4.12.3
python-dotenv==1.0.1
pytest==8.2.2
pytest-asyncio==0.23.7
```

- [ ] **Step 2: Crea .env.example**

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
KEEPA_API_KEY=
AMAZON_WISHLIST_URL=https://www.amazon.it/hz/wishlist/ls/XXXXXX
CHECK_INTERVAL_HOURS=4
REPORT_DAY=friday
REPORT_TIME=19:00
DB_PATH=/app/data/tracker.db
```

- [ ] **Step 3: Crea .gitignore**

```
.env
data/
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
dist/
.venv/
venv/
```

- [ ] **Step 4: Crea Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

CMD ["python", "src/main.py"]
```

- [ ] **Step 5: Crea docker-compose.yml**

```yaml
services:
  price-tracker:
    build: .
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./data:/app/data
```

- [ ] **Step 6: Crea tests/conftest.py**

```python
import pytest
import tempfile
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

@pytest.fixture
def tmp_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    from database import init_db
    init_db(db_path)
    return db_path
```

- [ ] **Step 7: Crea src/__init__.py e tests/__init__.py vuoti**

```bash
touch src/__init__.py tests/__init__.py
```

- [ ] **Step 8: Commit**

```bash
git add requirements.txt .env.example .gitignore Dockerfile docker-compose.yml src/__init__.py tests/__init__.py tests/conftest.py
git commit -m "feat: project scaffold"
```

---

## Task 2: Config Module

**Files:**
- Create: `src/config.py`

- [ ] **Step 1: Crea src/config.py**

```python
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    telegram_token: str
    telegram_chat_id: int
    keepa_api_key: str
    wishlist_url: str
    check_interval_hours: int
    report_day: str
    report_time: str
    db_path: str

def load_config() -> Config:
    return Config(
        telegram_token=os.environ["TELEGRAM_BOT_TOKEN"],
        telegram_chat_id=int(os.environ["TELEGRAM_CHAT_ID"]),
        keepa_api_key=os.environ["KEEPA_API_KEY"],
        wishlist_url=os.environ["AMAZON_WISHLIST_URL"],
        check_interval_hours=int(os.environ.get("CHECK_INTERVAL_HOURS", "4")),
        report_day=os.environ.get("REPORT_DAY", "friday"),
        report_time=os.environ.get("REPORT_TIME", "19:00"),
        db_path=os.environ.get("DB_PATH", "/app/data/tracker.db"),
    )
```

- [ ] **Step 2: Verifica che il modulo si importi senza errori con variabili mancanti**

```bash
cd /path/to/price-tracker
python -c "import sys; sys.path.insert(0,'src'); from config import Config, load_config; print('OK')"
```

Expected output: `OK` (nessuna eccezione all'import, eccezione solo alla chiamata di `load_config()` se mancano le env var)

- [ ] **Step 3: Commit**

```bash
git add src/config.py
git commit -m "feat: config module"
```

---

## Task 3: Database Layer

**Files:**
- Create: `src/database.py`
- Create: `tests/test_database.py`

- [ ] **Step 1: Scrivi test_database.py**

```python
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
```

- [ ] **Step 2: Esegui i test — devono fallire**

```bash
cd /path/to/price-tracker && pytest tests/test_database.py -v
```

Expected: `ModuleNotFoundError: No module named 'database'` o simile.

- [ ] **Step 3: Crea src/database.py**

```python
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
        return get_product_by_id(db_path, cursor.lastrowid)


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
```

- [ ] **Step 4: Esegui i test — devono passare**

```bash
pytest tests/test_database.py -v
```

Expected: tutti i test `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add src/database.py tests/test_database.py
git commit -m "feat: database layer with SQLite"
```

---

## Task 5: Scraper (Wishlist + Price Fetching)

**Files:**
- Create: `src/scraper.py`
- Create: `tests/test_scraper.py`

- [ ] **Step 1: Scrivi test_scraper.py**

```python
import pytest
from bs4 import BeautifulSoup
from scraper import _extract_asins_from_page, _get_next_page_url, _parse_price_text, _extract_items_from_wishlist_page, _extract_price_from_product_page

WISHLIST_HTML = """
<html><body>
  <li data-id="item1">
    <a id="itemName_item1" href="/Sony/dp/B09XS7JWHH/ref=wl">Sony WH-1000XM5</a>
    <span data-asin="B09XS7JWHH"></span>
    <span class="a-price"><span class="a-offscreen">€ 219,99</span></span>
  </li>
  <li data-id="item2">
    <a id="itemName_item2" href="/iPad/dp/B0BJLF2BRM/ref=wl">iPad Air</a>
    <span data-asin="B0BJLF2BRM"></span>
    <span class="a-price"><span class="a-offscreen">€ 749,00</span></span>
  </li>
  <a id="wishlistPaginationBar-next" href="/hz/wishlist/ls/ABC?page=2">Next</a>
</body></html>
"""

PRODUCT_PAGE_HTML = """
<html><body>
  <div id="corePriceDisplay_desktop_feature_div">
    <span class="a-price"><span class="a-offscreen">€ 219,99</span></span>
  </div>
</body></html>
"""

def test_parse_price_text_euro_comma():
    assert _parse_price_text("€ 219,99") == pytest.approx(219.99)

def test_parse_price_text_dot_separator():
    assert _parse_price_text("219.99") == pytest.approx(219.99)

def test_parse_price_text_no_price():
    assert _parse_price_text("Nessun prezzo") is None

def test_extract_items_from_wishlist_page():
    soup = BeautifulSoup(WISHLIST_HTML, "html.parser")
    items = _extract_items_from_wishlist_page(soup)
    assert len(items) == 2
    asins = [i["asin"] for i in items]
    assert "B09XS7JWHH" in asins
    assert "B0BJLF2BRM" in asins

def test_extract_items_prices():
    soup = BeautifulSoup(WISHLIST_HTML, "html.parser")
    items = _extract_items_from_wishlist_page(soup)
    sony = next(i for i in items if i["asin"] == "B09XS7JWHH")
    assert sony["price"] == pytest.approx(219.99)
    assert "Sony" in sony["name"]

def test_extract_price_from_product_page():
    soup = BeautifulSoup(PRODUCT_PAGE_HTML, "html.parser")
    price = _extract_price_from_product_page(soup)
    assert price == pytest.approx(219.99)

def test_get_next_page_url_present():
    soup = BeautifulSoup(WISHLIST_HTML, "html.parser")
    url = _get_next_page_url(soup, "https://www.amazon.it/hz/wishlist/ls/ABC")
    assert url is not None
    assert "page=2" in url

def test_get_next_page_url_absent():
    soup = BeautifulSoup("<html><body></body></html>", "html.parser")
    assert _get_next_page_url(soup, "https://www.amazon.it/hz/wishlist/ls/ABC") is None
```

- [ ] **Step 2: Esegui i test — devono fallire**

```bash
cd /Users/francesconegretti/Development/price-tracker && python -m pytest tests/test_scraper.py -v
```

Expected: `ModuleNotFoundError: No module named 'scraper'`

- [ ] **Step 3: Crea src/scraper.py**

```python
import re
from typing import Optional
import requests
from bs4 import BeautifulSoup

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Multiple price selectors in order of preference (Amazon changes HTML occasionally)
_PRICE_SELECTORS = [
    "#corePriceDisplay_desktop_feature_div .a-price .a-offscreen",
    "#apex_desktop .a-price .a-offscreen",
    "#priceblock_ourprice",
    "#priceblock_dealprice",
    ".a-price .a-offscreen",
]


def scrape_wishlist(wishlist_url: str) -> list:
    """Scarica la wishlist pubblica e ritorna lista di {asin, name, url, price}."""
    items = []
    url = wishlist_url
    while url:
        response = requests.get(url, headers=_HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        items.extend(_extract_items_from_wishlist_page(soup))
        url = _get_next_page_url(soup, wishlist_url)
    seen = set()
    unique = []
    for item in items:
        if item["asin"] not in seen:
            seen.add(item["asin"])
            unique.append(item)
    return unique


def fetch_product_info(product_url: str) -> Optional[dict]:
    """Recupera nome, ASIN e prezzo da una singola pagina prodotto Amazon."""
    try:
        response = requests.get(product_url, headers=_HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        asin = _extract_asin_from_url(product_url)
        name_el = soup.find("span", {"id": "productTitle"})
        name = name_el.get_text(strip=True) if name_el else "Prodotto senza nome"
        price = _extract_price_from_product_page(soup)
        if not asin:
            return None
        return {"asin": asin, "name": name, "url": product_url, "price": price}
    except Exception:
        return None


def fetch_current_price(product_url: str) -> Optional[float]:
    """Recupera solo il prezzo corrente da una pagina prodotto Amazon."""
    try:
        response = requests.get(product_url, headers=_HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        return _extract_price_from_product_page(soup)
    except Exception:
        return None


def _extract_items_from_wishlist_page(soup: BeautifulSoup) -> list:
    items = []
    for item_el in soup.find_all("li", attrs={"data-id": True}):
        asin_el = item_el.find(attrs={"data-asin": re.compile(r"^[A-Z0-9]{10}$")})
        if not asin_el:
            continue
        asin = asin_el.get("data-asin")
        name_el = item_el.find("a", {"id": re.compile(r"itemName")})
        name = name_el.get_text(strip=True) if name_el else "Prodotto senza nome"
        price = None
        price_el = item_el.find(class_="a-price")
        if price_el:
            offscreen = price_el.find(class_="a-offscreen")
            if offscreen:
                price = _parse_price_text(offscreen.get_text(strip=True))
        items.append({"asin": asin, "name": name, "url": f"https://www.amazon.it/dp/{asin}", "price": price})
    return items


def _extract_price_from_product_page(soup: BeautifulSoup) -> Optional[float]:
    for selector in _PRICE_SELECTORS:
        el = soup.select_one(selector)
        if el:
            price = _parse_price_text(el.get_text(strip=True))
            if price is not None:
                return price
    return None


def _parse_price_text(text: str) -> Optional[float]:
    match = re.search(r"(\d+)[.,](\d{2})", text.replace(".", "").replace(",", ".").strip())
    if match:
        try:
            return float(f"{match.group(1)}.{match.group(2)}")
        except ValueError:
            pass
    # fallback: cerca pattern numerico semplice dopo sostituzione
    clean = re.sub(r"[^\d.,]", "", text)
    clean = clean.replace(".", "").replace(",", ".")
    match2 = re.search(r"\d+\.\d{2}", clean)
    if match2:
        try:
            return float(match2.group())
        except ValueError:
            pass
    return None


def _get_next_page_url(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    next_link = soup.find("a", {"id": "wishlistPaginationBar-next"})
    if not next_link:
        return None
    href = next_link.get("href", "")
    if not href:
        return None
    return href if href.startswith("http") else "https://www.amazon.it" + href


def _extract_asin_from_url(url: str) -> Optional[str]:
    match = re.search(r"/dp/([A-Z0-9]{10})", url)
    return match.group(1) if match else None
```

- [ ] **Step 4: Esegui i test — devono passare**

```bash
cd /Users/francesconegretti/Development/price-tracker && python -m pytest tests/test_scraper.py -v
```

Expected: tutti `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add src/scraper.py tests/test_scraper.py
git commit -m "feat: scraper with wishlist import and price fetching"
```

---

## Task 6: Alert Logic

**Files:**
- Create: `src/scheduler.py` (parziale — solo `should_send_alert`)
- Create: `tests/test_scheduler.py` (parziale)

- [ ] **Step 1: Scrivi i test per should_send_alert in tests/test_scheduler.py**

```python
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
    # prezzo precedente era 195 (sotto target), ora scende a 180
    assert should_send_alert(180.0, 200.0, _ts(1), 195.0) is True

def test_no_alert_price_unchanged_within_24h():
    # prezzo invariato a 190, alert già inviato 12h fa
    assert should_send_alert(190.0, 200.0, _ts(12), 190.0) is False

def test_alert_price_unchanged_after_24h():
    # prezzo invariato a 190, ma l'ultimo alert era 25h fa
    assert should_send_alert(190.0, 200.0, _ts(25), 190.0) is True

def test_alert_price_at_exact_target():
    assert should_send_alert(200.0, 200.0, None, None) is True

def test_no_alert_above_target_even_with_old_alert():
    assert should_send_alert(210.0, 200.0, _ts(48), None) is False
```

- [ ] **Step 2: Esegui i test — devono fallire**

```bash
pytest tests/test_scheduler.py -v
```

Expected: `ModuleNotFoundError: No module named 'scheduler'`

- [ ] **Step 3: Crea src/scheduler.py con should_send_alert**

```python
from datetime import datetime, timedelta
from typing import Optional, Callable, Awaitable
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
    # Prezzo cambiato mentre è sotto target → notifica sempre
    if previous_price is not None and current_price != previous_price:
        return True
    # Prima volta sotto target
    if last_alert_at is None:
        return True
    # Prezzo invariato: notifica solo se sono passate 24h dall'ultimo alert
    last = datetime.fromisoformat(last_alert_at)
    return (datetime.utcnow() - last) >= timedelta(hours=24)
```

- [ ] **Step 4: Esegui i test — devono passare**

```bash
pytest tests/test_scheduler.py -v
```

Expected: tutti `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add src/scheduler.py tests/test_scheduler.py
git commit -m "feat: alert logic (should_send_alert)"
```

---

## Task 7: Price Check & Report Jobs

**Files:**
- Modify: `src/scheduler.py` (aggiungi `run_price_check`, `run_weekly_report`, `create_scheduler`)
- Modify: `tests/test_scheduler.py` (aggiungi test per i job)

- [ ] **Step 1: Aggiungi i test per run_price_check e run_weekly_report in tests/test_scheduler.py**

Aggiungi in fondo al file esistente:

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
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
```

- [ ] **Step 2: Esegui i test — devono fallire**

```bash
pytest tests/test_scheduler.py -v -k "price_check or weekly_report"
```

Expected: `ImportError` o `AttributeError` su `run_price_check`.

- [ ] **Step 3: Aggiungi run_price_check, run_weekly_report, create_scheduler in src/scheduler.py**

Aggiungi in fondo al file esistente:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler


async def run_price_check(db_path: str, send_alert: Callable) -> int:
    from database import get_all_products, update_product_price, update_last_alert
    from scraper import fetch_current_price

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
```

- [ ] **Step 4: Aggiungi pytest-asyncio mode in pytest.ini (oppure pyproject.toml)**

Crea `pytest.ini` nella root del progetto:

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 5: Esegui tutti i test — devono passare**

```bash
pytest tests/ -v
```

Expected: tutti `PASSED`.

- [ ] **Step 6: Commit**

```bash
git add src/scheduler.py tests/test_scheduler.py pytest.ini
git commit -m "feat: price check and weekly report scheduler jobs"
```

---

## Task 8: Telegram Bot

**Files:**
- Create: `src/bot.py`

I handler del bot dipendono dall'infrastruttura Telegram (polling, webhook) e non si testano a livello unitario in questo piano. Il test è end-to-end (Task 10).

- [ ] **Step 1: Crea src/bot.py**

```python
import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)


def _owner_only(handler):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user:
            return
        if update.effective_user.id != context.bot_data["chat_id"]:
            logger.warning("Accesso negato a user_id=%s", update.effective_user.id)
            return
        return await handler(update, context)
    return wrapper


@_owner_only
async def _cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 *Amazon Price Tracker*\n\n"
        "Comandi disponibili:\n"
        "/import — importa dalla wishlist Amazon\n"
        "/add <url> — aggiungi prodotto\n"
        "/list — mostra tutti i prodotti\n"
        "/remove <id> — rimuovi prodotto\n"
        "/target <id> <prezzo> — imposta target\n"
        "/check — controlla prezzi ora\n"
        "/status — stato del bot"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


@_owner_only
async def _cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import get_all_products
    products = get_all_products(context.bot_data["db_path"])

    if not products:
        await update.message.reply_text("Nessun prodotto in tracciamento.")
        return

    lines = []
    for p in products:
        price_str = f"€{p.current_price:.2f}" if p.current_price else "N/D"
        target_str = f"🎯 €{p.target_price:.2f}" if p.target_price else "nessun target"
        icon = "✅" if (p.current_price and p.target_price and p.current_price <= p.target_price) else "📦"
        lines.append(f"{icon} `{p.id}` *{p.name[:40]}*\n    💰 {price_str} — {target_str}")

    await update.message.reply_text("\n\n".join(lines), parse_mode=ParseMode.MARKDOWN)


@_owner_only
async def _cmd_import(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from scraper import scrape_wishlist
    from database import get_product_by_asin, add_product

    db_path = context.bot_data["db_path"]
    wishlist_url = context.bot_data["wishlist_url"]

    await update.message.reply_text("⏳ Importazione wishlist in corso...")

    try:
        items = scrape_wishlist(wishlist_url)
    except Exception as e:
        await update.message.reply_text(f"❌ Errore scraping wishlist: {e}")
        return

    new_items = [i for i in items if not get_product_by_asin(db_path, i["asin"])]
    if not new_items:
        await update.message.reply_text("Tutti i prodotti della wishlist sono già in tracciamento.")
        return

    for item in new_items:
        add_product(db_path, item["asin"], item["name"], item["url"], item["price"], "wishlist")

    skipped = len(items) - len(new_items)
    msg = f"✅ Importati {len(new_items)} prodotti"
    if skipped:
        msg += f", {skipped} già presenti."
    await update.message.reply_text(msg)


@_owner_only
async def _cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from scraper import fetch_product_info, _extract_asin_from_url
    from database import get_product_by_asin, add_product

    if not context.args:
        await update.message.reply_text("Uso: /add <url_amazon>")
        return

    db_path = context.bot_data["db_path"]
    url = context.args[0]

    asin = _extract_asin_from_url(url)
    if not asin:
        await update.message.reply_text("URL non valido. Deve contenere /dp/ASIN.")
        return

    if get_product_by_asin(db_path, asin):
        await update.message.reply_text("Prodotto già in tracciamento.")
        return

    await update.message.reply_text("⏳ Recupero informazioni...")
    info = fetch_product_info(url)
    if not info:
        await update.message.reply_text("Prodotto non trovato.")
        return

    product = add_product(db_path, info["asin"], info["name"], info["url"], info["price"], "manual")
    price_str = f"€{info['price']:.2f}" if info["price"] else "N/D"
    await update.message.reply_text(
        f"✅ Aggiunto: *{info['name']}*\n"
        f"💰 Prezzo attuale: {price_str}\n"
        f"Imposta target con: /target {product.id} <prezzo>",
        parse_mode=ParseMode.MARKDOWN,
    )


@_owner_only
async def _cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import get_product_by_id, remove_product

    if not context.args:
        await update.message.reply_text("Uso: /remove <id>")
        return

    db_path = context.bot_data["db_path"]
    try:
        product_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID non valido. Usa /list per vedere gli ID.")
        return

    product = get_product_by_id(db_path, product_id)
    if not product:
        await update.message.reply_text(f"Prodotto con ID {product_id} non trovato.")
        return

    remove_product(db_path, product_id)
    await update.message.reply_text(f"✅ Rimosso: {product.name}")


@_owner_only
async def _cmd_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import get_product_by_id, update_product_target

    if len(context.args) < 2:
        await update.message.reply_text("Uso: /target <id> <prezzo>")
        return

    db_path = context.bot_data["db_path"]
    try:
        product_id = int(context.args[0])
        target = float(context.args[1].replace(",", "."))
    except ValueError:
        await update.message.reply_text("ID o prezzo non valido. Esempio: /target 3 199.99")
        return

    product = get_product_by_id(db_path, product_id)
    if not product:
        await update.message.reply_text(f"Prodotto con ID {product_id} non trovato.")
        return

    update_product_target(db_path, product_id, target)
    await update.message.reply_text(
        f"🎯 Target impostato: *{product.name}* → €{target:.2f}",
        parse_mode=ParseMode.MARKDOWN,
    )


@_owner_only
async def _cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Controllo prezzi in corso...")
    await context.bot_data["run_price_check"]()
    await update.message.reply_text("✅ Controllo completato.")


@_owner_only
async def _cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    scheduler = context.bot_data["scheduler"]
    check_job = scheduler.get_job("price_check")
    report_job = scheduler.get_job("weekly_report")

    check_next = check_job.next_run_time.strftime("%d/%m/%Y %H:%M") if check_job else "N/D"
    report_next = report_job.next_run_time.strftime("%d/%m/%Y %H:%M") if report_job else "N/D"

    await update.message.reply_text(
        f"🤖 *Bot attivo*\n"
        f"⏰ Prossimo check: {check_next}\n"
        f"📊 Prossimo report: {report_next}",
        parse_mode=ParseMode.MARKDOWN,
    )


def build_application(token: str, bot_data: dict, post_init=None) -> Application:
    builder = Application.builder().token(token)
    if post_init:
        builder = builder.post_init(post_init)
    app = builder.build()
    app.bot_data.update(bot_data)

    app.add_handler(CommandHandler("start", _cmd_start))
    app.add_handler(CommandHandler("list", _cmd_list))
    app.add_handler(CommandHandler("import", _cmd_import))
    app.add_handler(CommandHandler("add", _cmd_add))
    app.add_handler(CommandHandler("remove", _cmd_remove))
    app.add_handler(CommandHandler("target", _cmd_target))
    app.add_handler(CommandHandler("check", _cmd_check))
    app.add_handler(CommandHandler("status", _cmd_status))

    return app
```

- [ ] **Step 2: Verifica che il modulo si importi senza errori**

```bash
cd /path/to/price-tracker && python -c "import sys; sys.path.insert(0,'src'); from bot import build_application; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Esegui la suite di test completa — deve rimanere verde**

```bash
pytest tests/ -v
```

Expected: tutti `PASSED`.

- [ ] **Step 4: Commit**

```bash
git add src/bot.py
git commit -m "feat: Telegram bot handlers"
```

---

## Task 9: Entry Point

**Files:**
- Create: `src/main.py`

- [ ] **Step 1: Crea src/main.py**

```python
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
        async def send_message(msg: str) -> None:
            await app.bot.send_message(
                config.telegram_chat_id, msg, parse_mode="Markdown"
            )

        async def price_check_job() -> None:
            count = await run_price_check(config.db_path, send_message)
            logger.info("Price check: %d alert inviati", count)

        async def weekly_report_job() -> None:
            await run_weekly_report(config.db_path, send_message)

        scheduler = create_scheduler(
            config.check_interval_hours,
            config.report_day,
            config.report_time,
            price_check_job,
            weekly_report_job,
        )
        app.bot_data["run_price_check"] = price_check_job
        app.bot_data["scheduler"] = scheduler
        scheduler.start()
        logger.info(
            "Scheduler avviato: check ogni %dh, report %s alle %s",
            config.check_interval_hours, config.report_day, config.report_time,
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
```

- [ ] **Step 2: Esegui la suite di test — deve rimanere verde**

```bash
pytest tests/ -v
```

Expected: tutti `PASSED`.

- [ ] **Step 3: Commit**

```bash
git add src/main.py
git commit -m "feat: entry point, wire bot + scheduler"
```

---

## Task 10: Deploy e Verifica

**Files:**
- Verify: `Dockerfile`, `docker-compose.yml`

- [ ] **Step 1: Copia .env.example in .env e compila le variabili**

```bash
cp .env.example .env
```

Valori da inserire in `.env`:
- `TELEGRAM_BOT_TOKEN`: crea il bot su @BotFather con `/newbot`
- `TELEGRAM_CHAT_ID`: ottieni il tuo chat ID scrivendo a @userinfobot
- `KEEPA_API_KEY`: registrati su keepa.com → Account → API Access
- `AMAZON_WISHLIST_URL`: URL della tua wishlist pubblica Amazon

- [ ] **Step 2: Build locale dell'immagine**

```bash
docker compose build
```

Expected: build completata senza errori.

- [ ] **Step 3: Avvia il container**

```bash
docker compose up
```

Expected log:
```
price-tracker  | Database inizializzato: /app/data/tracker.db
price-tracker  | Scheduler avviato: check ogni 4h, report friday alle 19:00
price-tracker  | Bot avviato. In ascolto...
```

- [ ] **Step 4: Test funzionale — invia /start al bot su Telegram**

Apri Telegram, scrivi `/start` al bot.  
Expected: risposta con la lista dei comandi.

- [ ] **Step 5: Test funzionale — aggiungi un prodotto**

```
/add https://www.amazon.it/dp/B09XS7JWHH
```

Expected: conferma con nome prodotto e prezzo corrente.

- [ ] **Step 6: Test funzionale — imposta target e forza check**

```
/target 1 200
/check
```

Expected: `/target` conferma il target impostato. `/check` risponde "Controllo completato" (e se il prezzo è ≤ 200, arriva un alert separato).

- [ ] **Step 7: Ferma il container e verifica la persistenza del DB**

```bash
docker compose down
docker compose up
/list
```

Expected: il prodotto aggiunto prima è ancora presente.

- [ ] **Step 8: Commit finale**

```bash
git add .
git commit -m "feat: complete price tracker bot — ready for CasaOS deploy"
```
