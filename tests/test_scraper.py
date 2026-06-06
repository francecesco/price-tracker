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
