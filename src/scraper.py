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


# Amazon carica i prodotti oltre i primi 10 via JavaScript (lazy loading).
# La paginazione ?page=N non funziona senza un browser headless.
# Workaround: scraping con ordinamenti diversi — ogni sort espone una top-10 diversa.
_SORT_ORDERS = [
    "default",
    "date-added-desc",
    "price-asc",
    "price-desc",
    "updated-desc",
    "priority-desc",
]


def scrape_wishlist(wishlist_url: str) -> list:
    """Scarica la wishlist pubblica e ritorna lista di {asin, name, url, price}.

    Usa più ordinamenti per aggirare il limite di 10 prodotti per pagina
    imposto da Amazon senza JavaScript.
    """
    logger = logging.getLogger(__name__)
    base_url = wishlist_url.split("?")[0]
    seen: set = set()
    items: list = []

    session = requests.Session()

    for sort in _SORT_ORDERS:
        url = f"{base_url}?sort={sort}"
        try:
            response = session.get(url, headers=_HEADERS, timeout=15)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.warning("Errore wishlist sort=%s: %s", sort, e)
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        page_items = _extract_items_from_wishlist_page(soup)
        new_items = [i for i in page_items if i["asin"] not in seen]
        logger.info("Sort %-18s: %d prodotti, %d nuovi", sort, len(page_items), len(new_items))

        for item in new_items:
            seen.add(item["asin"])
            items.append(item)

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
