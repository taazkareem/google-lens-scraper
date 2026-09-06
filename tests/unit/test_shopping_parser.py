"""SPDX-FileCopyrightText: © 2026 Talib Kareem <taazkareem@icloud.com>
SPDX-License-Identifier: MIT

Unit tests for Google Shopping SERP and comparison table parsing.
"""

import pytest

from google_lens_pro.core.exceptions import ShoppingParseError, ShoppingRateLimitError
from google_lens_pro.engines.shopping.parser import ShoppingParser
from google_lens_pro.models.common import ItemCondition, StockStatus


SAMPLE_SHOPPING_SERP_HTML = """
<!DOCTYPE html>
<html>
<body>
  <div class="sh-pr__product-results">
    <div class="sh-dgr__content" data-docid="item-1">
      <h3 class="tAxLfb">Sony WH-1000XM5 Wireless Headphones</h3>
      <a href="https://www.google.com/url?q=https://www.bestbuy.com/site/sony-headphones/12345.p">
        <span class="a8Pemb OFFBWs">$349.99</span>
      </a>
      <div class="aULzUe IxZjcf">Best Buy</div>
      <span aria-label="4.7 out of 5 stars">4.7 stars</span>
      <span>(3,420 reviews)</span>
      <div class="vEjExt">Free shipping</div>
    </div>

    <div class="sh-dgr__content" data-docid="item-2">
      <h3 class="tAxLfb">Sony WH-1000XM5 Noise Canceling Headphones - Black</h3>
      <a href="https://www.google.com/url?q=https://www.amazon.com/dp/B09XS7JWHH">
        <span class="a8Pemb OFFBWs">$328.00</span>
      </a>
      <div class="aULzUe IxZjcf">Amazon.com</div>
      <span aria-label="4.6 out of 5 stars">4.6 out of 5</span>
      <span>(12,850)</span>
      <div class="vEjExt">Free delivery</div>
    </div>

    <div class="sh-dgr__content" data-docid="item-3">
      <h3 class="tAxLfb">Sony WH-1000XM5 Refurbished</h3>
      <a href="https://www.google.com/url?q=https://www.ebay.com/itm/987654321">
        <span class="a8Pemb OFFBWs">$279.50</span>
      </a>
      <div class="aULzUe IxZjcf">eBay - TechDeals</div>
      <div class="vEjExt">Refurbished · $5.99 shipping</div>
    </div>
  </div>
</body>
</html>
"""

SAMPLE_COMPARISON_HTML = """
<!DOCTYPE html>
<html>
<body>
  <h1>Apple AirPods Pro (2nd Generation)</h1>
  <table>
    <tr class="sh-osd__offer-row">
      <td><a href="https://www.google.com/url?q=https://www.target.com/p/airpods-pro">Target</a></td>
      <td>$189.99</td>
      <td>Free shipping</td>
    </tr>
    <tr class="sh-osd__offer-row">
      <td><a href="https://www.google.com/url?q=https://www.walmart.com/ip/airpods-pro">Walmart</a></td>
      <td>$199.00</td>
      <td>Free 2-day delivery</td>
    </tr>
  </table>
</body>
</html>
"""


def test_check_html_validation():
    """Verify empty and challenge HTML detections."""
    with pytest.raises(ShoppingParseError, match="Empty HTML"):
        ShoppingParser.check_html("")

    with pytest.raises(ShoppingRateLimitError, match="/sorry/index"):
        ShoppingParser.check_html("<html><title>Google</title><body>sorry/index block</body></html>")

    with pytest.raises(ShoppingRateLimitError, match="unusual traffic"):
        ShoppingParser.check_html("<html>Our systems have detected unusual traffic from your network.</html>")


def test_parse_serp_offers():
    """Verify extraction of product cards, prices, ratings, and best deal."""
    result = ShoppingParser.parse_serp(SAMPLE_SHOPPING_SERP_HTML, query="Sony WH-1000XM5")

    assert result.query == "Sony WH-1000XM5"
    assert result.total_offers == 3
    assert len(result.offers) == 3

    # Check offer 1 (Best Buy)
    o1 = result.offers[0]
    assert "Sony WH-1000XM5" in o1.title
    assert o1.price is not None
    assert o1.price.amount == 349.99
    assert o1.price.currency == "USD"
    assert "bestbuy.com" in (o1.direct_url or "")
    assert o1.rating == 4.7
    assert o1.review_count == 3420
    assert o1.shipping_info == "Free shipping"

    # Check offer 2 (Amazon)
    o2 = result.offers[1]
    assert o2.price.amount == 328.00
    assert "amazon.com" in (o2.direct_url or "")
    assert o2.rating == 4.6
    assert o2.review_count == 12850

    # Check offer 3 (eBay refurbished)
    o3 = result.offers[2]
    assert o3.price.amount == 279.50
    assert o3.condition == ItemCondition.REFURBISHED

    # Summary analytics
    assert result.min_price == 279.50
    assert result.max_price == 349.99
    assert result.avg_price == round((349.99 + 328.00 + 279.50) / 3, 2)
    assert result.best_deal is not None
    assert result.best_deal.price.amount == 279.50


def test_parse_comparison_page():
    """Verify parsing multi-seller comparison table."""
    comparison = ShoppingParser.parse_comparison_page(SAMPLE_COMPARISON_HTML, product_id="1234567")

    assert comparison.product_id == "1234567"
    assert "Apple AirPods Pro" in comparison.title
    assert len(comparison.sellers) == 2

    s1 = comparison.sellers[0]
    assert s1.price.amount == 189.99
    assert "target.com" in (s1.direct_url or "")

    s2 = comparison.sellers[1]
    assert s2.price.amount == 199.00
    assert "walmart.com" in (s2.direct_url or "")
