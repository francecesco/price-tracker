import re
import logging
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

_PRICE_SELECTORS = [
    "#corePriceDisplay_desktop_feature_div .a-price .a-offscreen",
    "#apex_desktop .a-price .a-offscreen",
    "#priceblock_ourprice",
    "#priceblock_dealprice",
    ".a-price .a-offscreen",
]


async def scrape_wishlist(wishlist_url: str) -> list:
    """Scarica la wishlist pubblica usando Playwright per eseguire JavaScript.

    Scrolla la pagina finché non compaiono nuovi prodotti, poi estrae tutto.
    """
    from playwright.async_api import async_playwright

    logger = logging.getLogger(__name__)
    seen: set = set()
    items: list = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        page = await browser.new_page(user_agent=_HEADERS["User-Agent"])
        await page.set_extra_http_headers({"Accept-Language": _HEADERS["Accept-Language"]})

        try:
            await page.goto(wishlist_url, wait_until="networkidle", timeout=30000)

            # Accetta cookie GDPR se presente
            try:
                await page.click("#sp-cc-accept", timeout=3000)
                await page.wait_for_timeout(1000)
            except Exception:
                pass

            # Scrolla finché il numero di prodotti non si stabilizza
            prev_count = 0
            for attempt in range(20):
                count = await page.locator("[data-asin]").count()
                logger.info("Scroll %d: %d elementi trovati", attempt + 1, count)
                if count > 0 and count == prev_count:
                    break
                prev_count = count
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1500)

            html = await page.content()
        finally:
            await browser.close()

    soup = BeautifulSoup(html, "html.parser")
    page_items = _extract_items_from_wishlist_page(soup)
    for item in page_items:
        if item["asin"] not in seen:
            seen.add(item["asin"])
            items.append(item)

    logger.info("Playwright: trovati %d prodotti unici", len(items))
    return items


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
    seen: set = set()

    # Strategia 1: li con data-id o id che inizia con "item"
    containers = (
        soup.find_all("li", attrs={"data-id": True})
        or soup.find_all("li", id=re.compile(r"^item"))
    )
    for item_el in containers:
        asin_el = item_el.find(attrs={"data-asin": re.compile(r"^[A-Z0-9]{10}$")})
        asin = asin_el.get("data-asin") if asin_el else None
        if not asin:
            link = item_el.find("a", href=re.compile(r"/dp/[A-Z0-9]{10}"))
            if link:
                m = re.search(r"/dp/([A-Z0-9]{10})", link["href"])
                asin = m.group(1) if m else None
        if not asin or asin in seen:
            continue
        seen.add(asin)

        name_el = item_el.find("a", id=re.compile(r"itemName")) or item_el.find(
            "a", href=re.compile(r"/dp/" + asin)
        )
        name = (name_el.get_text(strip=True) or name_el.get("title", "")) if name_el else ""
        name = name or "Prodotto senza nome"

        price = None
        price_el = item_el.find(class_="a-price")
        if price_el:
            offscreen = price_el.find(class_="a-offscreen")
            if offscreen:
                price = _parse_price_text(offscreen.get_text(strip=True))
        if price is None:
            dp = item_el.get("data-price")
            if dp and dp != "-Infinity":
                try:
                    price = float(dp) / 100
                except (ValueError, TypeError):
                    pass

        items.append({"asin": asin, "name": name, "url": f"https://www.amazon.it/dp/{asin}", "price": price})

    # Strategia 2 (fallback): estrae ASIN da tutti i link /dp/ della pagina
    if not items:
        logging.getLogger(__name__).warning("Strategia strutturata vuota, uso fallback sui link prodotto")
        for link in soup.find_all("a", href=re.compile(r"/dp/[A-Z0-9]{10}")):
            m = re.search(r"/dp/([A-Z0-9]{10})", link["href"])
            if not m:
                continue
            asin = m.group(1)
            if asin in seen:
                continue
            seen.add(asin)
            name = link.get_text(strip=True) or link.get("title", "Prodotto senza nome") or "Prodotto senza nome"
            items.append({"asin": asin, "name": name, "url": f"https://www.amazon.it/dp/{asin}", "price": None})

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
    # Normalise: remove currency symbols and spaces, then parse
    cleaned = text.strip()
    # Handle Italian format: "219,99" or "€ 219,99" or "1.234,56"
    # Remove thousands dots, replace decimal comma with dot
    # First extract digits, comma/dot pattern
    match = re.search(r"(\d{1,3}(?:\.\d{3})*),(\d{2})\b", cleaned)
    if match:
        integer_part = match.group(1).replace(".", "")
        return float(f"{integer_part}.{match.group(2)}")
    # Fallback: plain decimal with dot
    match2 = re.search(r"(\d+)\.(\d{2})\b", cleaned)
    if match2:
        return float(f"{match2.group(1)}.{match2.group(2)}")
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


def _extract_asins_from_page(soup: BeautifulSoup) -> list:
    """Kept for backward compatibility — extracts only ASINs (no prices)."""
    asins = []
    for link in soup.find_all("a", href=re.compile(r"/dp/[A-Z0-9]{10}")):
        match = re.search(r"/dp/([A-Z0-9]{10})", link["href"])
        if match:
            asins.append(match.group(1))
    for el in soup.find_all(attrs={"data-asin": re.compile(r"^[A-Z0-9]{10}$")}):
        asins.append(el["data-asin"])
    return list(dict.fromkeys(asins))
