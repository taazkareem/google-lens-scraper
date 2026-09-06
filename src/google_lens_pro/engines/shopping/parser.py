"""SPDX-FileCopyrightText: © 2026 Talib Kareem <taazkareem@icloud.com>
SPDX-License-Identifier: MIT

HTML parser for Google Shopping search result grids, listing cards, and product comparison tables.
"""

from __future__ import annotations

import html as html_lib
import logging
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from ...commerce.classifier import MerchantClassifier
from ...commerce.normalizer import PriceNormalizer
from ...commerce.unwrapper import URLUnwrapper
from ...core.exceptions import ShoppingParseError, ShoppingRateLimitError
from ...models.common import ItemCondition, StockStatus
from ...models.shopping import ShoppingComparison, ShoppingOffer, ShoppingResult

logger = logging.getLogger(__name__)

# Regular expressions for Google Shopping SERP card extraction
_CARD_CONTAINER_PATTERN = re.compile(
    r'(<div[^>]*class=["\'][^"\']*(?:sh-dgr__content|sh-dlr__content|pla-unit|KZmu8e|sh-pr__product-results)[^"\']*["\'].*?)(?=<div[^>]*class=["\'][^"\']*(?:sh-dgr__content|sh-dlr__content|pla-unit|KZmu8e|sh-pr__product-results)|$)',
    re.DOTALL | re.IGNORECASE,
)

_PRICE_PATTERN = re.compile(
    r'[\$€£¥₹]\s*\d+(?:[,\.]\d+)*(?:\s*(?:USD|EUR|GBP|CAD|AUD|INR|JPY|CNY))?'
    r'|\d+(?:[,\.]\d+)*\s*(?:[\$€£¥₹]|USD|EUR|GBP|CAD|AUD|INR|JPY|CNY)',
    re.IGNORECASE,
)

_RATING_PATTERN = re.compile(r'([0-5](?:\.[0-9])?)\s*(?:out of 5|\s*stars|\s*★)', re.IGNORECASE)
_REVIEWS_PATTERN = re.compile(r'\(([\d,]+)\s*(?:reviews?|ratings?)?\)', re.IGNORECASE)

# Direct search templates for major marketplaces and retail platforms
_STORE_SEARCH_TEMPLATES: dict[str, str] = {
    "stockx": "https://stockx.com/search?s={query}",
    "goat": "https://www.goat.com/search?query={query}",
    "flight club": "https://www.flightclub.com/catalogsearch/result?query={query}",
    "ebay": "https://www.ebay.com/sch/i.html?_nkw={query}",
    "walmart": "https://www.walmart.com/search?q={query}",
    "target": "https://www.target.com/s?searchTerm={query}",
    "best buy": "https://www.bestbuy.com/site/searchpage.jsp?st={query}",
    "amazon": "https://www.amazon.com/s?k={query}",
    "lyst": "https://www.lyst.com/search/?q={query}",
    "editorialist": "https://editorialist.com/search?query={query}",
    "modesens": "https://modesens.com/products/?q={query}",
    "grailed": "https://www.grailed.com/shop?query={query}",
    "poshmark": "https://poshmark.com/search?query={query}",
    "mercari": "https://www.mercari.com/search/?keyword={query}",
    "nike": "https://www.nike.com/w?q={query}",
    "adidas": "https://www.adidas.com/us/search?q={query}",
    "nordstrom": "https://www.nordstrom.com/sr?origin=keywordsearch&keyword={query}",
    "ssense": "https://www.ssense.com/en-us/men?q={query}",
    "farfetch": "https://www.farfetch.com/shopping/men/search/items.aspx?q={query}",
    "stadium goods": "https://www.stadiumgoods.com/search?q={query}",
}


def _resolve_merchant_url(merchant: str, title: str, product_id: str | None = None) -> str:
    """Resolves an actionable store URL when Google Shopping omits direct outbound links."""
    from urllib.parse import quote_plus

    m_lower = merchant.lower().strip()
    for key, template in _STORE_SEARCH_TEMPLATES.items():
        if key in m_lower:
            return template.format(query=quote_plus(title))
    if "." in merchant and " " not in merchant:
        return f"https://{merchant}"
    if product_id:
        return f"https://www.google.com/shopping/product/{product_id}"
    return f"https://www.google.com/search?q={quote_plus(merchant)}+{quote_plus(title)}"


class ShoppingParser:
    """Parses Google Shopping SERPs and comparative product pages."""

    @staticmethod
    def check_html(html: str) -> None:
        """Raises if the HTML represents a bot detection or CAPTCHA challenge."""
        if not html:
            raise ShoppingParseError("Empty HTML response received from Google Shopping.")
        if ("sorry/index" in html and len(html) < 50_000) or ("enablejs" in html and len(html) < 150_000):
            raise ShoppingRateLimitError(
                "Google Shopping rate limit or bot challenge triggered (/sorry/index or enablejs).",
                status_code=429,
            )
        if "Our systems have detected unusual traffic" in html:
            raise ShoppingRateLimitError(
                "Google Shopping rate limit / CAPTCHA detected (unusual traffic).",
                status_code=429,
            )

    @classmethod
    def parse_serp(
        cls,
        html: str,
        query: str = "",
        currency_hint: str = "USD",
    ) -> ShoppingResult:
        """Parses Google Shopping search results HTML (udm=28 / tbm=shop) into a structured ShoppingResult."""
        cls.check_html(html)

        offers: list[ShoppingOffer] = []
        seen_urls: set[str] = set()

        # Try parsing with lxml if available, otherwise regex fallback
        try:
            from lxml import html as lxml_html

            tree = lxml_html.fromstring(html)
            offers = cls._parse_with_lxml(tree, currency_hint=currency_hint)
        except Exception as e:
            logger.debug("lxml shopping parse failed (%s), falling back to regex: %s", e, e)
            offers = cls._parse_with_regex(html, currency_hint=currency_hint)

        # Deduplicate offers by clean direct_url
        unique_offers: list[ShoppingOffer] = []
        for o in offers:
            key = (o.direct_url or o.original_url).lower().strip()
            if not key or key in seen_urls:
                continue
            seen_urls.add(key)
            unique_offers.append(o)

        # Compute summary metrics
        priced_amounts = [o.price.amount for o in unique_offers if o.price and o.price.amount > 0]
        min_price = min(priced_amounts) if priced_amounts else None
        max_price = max(priced_amounts) if priced_amounts else None
        avg_price = (
            round(sum(priced_amounts) / len(priced_amounts), 2) if priced_amounts else None
        )

        # Find best deal (lowest verified in-stock price)
        best_deal = None
        in_stock_offers = [
            o
            for o in unique_offers
            if o.price and o.price.amount > 0 and o.stock_status != StockStatus.OUT_OF_STOCK
        ]
        if in_stock_offers:
            best_deal = min(in_stock_offers, key=lambda x: x.price.amount)

        dominant_currency = unique_offers[0].price.currency if unique_offers else currency_hint

        return ShoppingResult(
            query=query,
            total_offers=len(unique_offers),
            offers=unique_offers,
            min_price=min_price,
            max_price=max_price,
            avg_price=avg_price,
            currency=dominant_currency,
            best_deal=best_deal,
        )

    @classmethod
    def _parse_with_lxml(
        cls,
        tree: Any,
        currency_hint: str = "USD",
    ) -> list[ShoppingOffer]:
        """Parses Google Shopping cards using lxml XPath and CSS selectors."""
        offers: list[ShoppingOffer] = []

        # Find product card elements
        card_selectors = [
            "//div[contains(@class, 'UC8ZCe')]",
            "//div[contains(@class, 'sh-dgr__content')]",
            "//div[contains(@class, 'sh-dlr__content')]",
            "//div[contains(@class, 'pla-unit')]",
            "//div[contains(@class, 'KZmu8e')]",
            "//div[contains(@class, 'sh-pr__product-results')]",
            "//div[@data-docid]",
        ]

        cards = []
        for sel in card_selectors:
            found = tree.xpath(sel)
            if found:
                cards = found
                break

        if not cards:
            # Fallback to scanning all anchor tags that look like shopping results
            cards = tree.xpath("//div[.//a[contains(@href, '/shopping/product/') or contains(@href, '/url?')]]")

        for card in cards:
            offer = cls._extract_card_lxml(card, currency_hint=currency_hint)
            if offer and offer.price and offer.title:
                offers.append(offer)

        return offers

    @classmethod
    def _extract_card_lxml(cls, card: Any, currency_hint: str = "USD") -> ShoppingOffer | None:
        """Extracts a single ShoppingOffer from an lxml element card."""
        try:
            # 1. Title
            title = ""
            title_nodes = card.xpath(".//div[contains(@class, 'gkQHve')] | .//h3 | .//h4 | .//*[contains(@class, 'tAxLfb')] | .//*[contains(@class, 'sh-o__title-link')]")
            if title_nodes:
                title = title_nodes[0].text_content().strip()

            # 2. Link / URL
            link = ""
            link_nodes = card.xpath(".//a[contains(@href, 'http') or contains(@href, '/shopping/product/') or contains(@href, '/url?')]")
            if link_nodes:
                link = link_nodes[0].get("href", "").strip()

            if not link and not title:
                return None

            if link.startswith("/"):
                link = f"https://www.google.com{link}"

            direct_url = URLUnwrapper.unwrap(link) if link else ""

            # 3. Price
            raw_text = card.text_content()
            price = None
            price_nodes = card.xpath(".//*[contains(@class, 'lmQWe')] | .//*[contains(@class, 'a8Pemb')] | .//*[contains(@class, 'H8A25b')] | .//*[contains(@class, 'kHDAkb')] | .//span[contains(text(), '$') or contains(text(), '€') or contains(text(), '£')]")
            if price_nodes:
                for pn in price_nodes:
                    parsed = PriceNormalizer.parse(pn.text_content(), currency_hint=currency_hint)
                    if parsed:
                        price = parsed
                        break

            if not price:
                m_price = _PRICE_PATTERN.search(raw_text)
                if m_price:
                    price = PriceNormalizer.parse(m_price.group(0), currency_hint=currency_hint)

            if not price:
                return None

            original_price = None
            orig_nodes = card.xpath(".//*[contains(@class, 'DoCHT')]")
            if orig_nodes:
                original_price = PriceNormalizer.parse(orig_nodes[0].text_content().strip(), currency_hint=currency_hint)

            # 4. Merchant Name
            merchant_name = ""
            merchant_nodes = card.xpath(".//*[contains(@class, 'WJMUdc')] | .//*[contains(@class, 'aULzUe')] | .//*[contains(@class, 'dD8iuc')] | .//*[contains(@class, 'IuHnof')] | .//*[contains(@class, 'vEjMR')]")
            if merchant_nodes:
                merchant_name = merchant_nodes[0].text_content().strip()
            if not merchant_name:
                domain = URLUnwrapper.extract_domain(direct_url)
                merchant_name = domain.split(".")[0].title() if domain else "Online Merchant"

            # Clean merchant name
            if "·" in merchant_name:
                merchant_name = merchant_name.split("·")[0].strip()
            if "," in merchant_name:
                merchant_name = merchant_name.split(",")[0].strip()

            # 5. Product docid / cluster ID (check link, card, and ancestors)
            product_id = None
            m_doc = re.search(r'/shopping/product/(\d+)', link)
            if m_doc:
                product_id = m_doc.group(1)
            else:
                for anc in [card] + list(card.iterancestors()):
                    for attr in ("data-gid", "data-pid", "data-docid", "data-cid"):
                        val = anc.get(attr)
                        if val and val.isdigit():
                            product_id = val
                            break
                    if product_id:
                        break

            # If no direct merchant link or internal Google redirect, resolve to actionable store URL
            if (
                not direct_url
                or "google.com/search" in direct_url
                or direct_url.startswith("https://support.google.com")
                or direct_url.startswith("https://policies.google.com")
            ):
                direct_url = _resolve_merchant_url(merchant_name, title, product_id=product_id)
                link = direct_url

            # Merchant category
            domain = URLUnwrapper.extract_domain(direct_url) or merchant_name
            category = MerchantClassifier.classify(domain=domain, title=title, merchant_name=merchant_name)

            # 5. Thumbnail
            thumbnail = None
            img_nodes = card.xpath(".//img[@src]")
            if img_nodes:
                src = img_nodes[0].get("src")
                if src and "data:image" not in src:
                    thumbnail = src

            # 6. Ratings & Reviews
            rating = None
            review_count = None
            rating_nodes = card.xpath(".//*[contains(@class, 'yi40Hd')]")
            if rating_nodes:
                try:
                    rating = float(rating_nodes[0].text_content().strip())
                except ValueError:
                    pass

            if rating is None:
                m_rating = _RATING_PATTERN.search(raw_text)
                if m_rating:
                    try:
                        rating = float(m_rating.group(1))
                    except ValueError:
                        pass

            review_nodes = card.xpath(".//*[contains(@class, 'RDApEe')]")
            if review_nodes:
                m_rev = re.search(r'([\d\.]+[KkMm]?)', review_nodes[0].text_content())
                if m_rev:
                    val = m_rev.group(1).upper()
                    try:
                        if 'K' in val:
                            review_count = int(float(val.replace('K', '')) * 1000)
                        elif 'M' in val:
                            review_count = int(float(val.replace('M', '')) * 1000000)
                        else:
                            review_count = int(val.replace(',', ''))
                    except ValueError:
                        pass

            if review_count is None:
                m_reviews = _REVIEWS_PATTERN.search(raw_text)
                if m_reviews:
                    try:
                        review_count = int(m_reviews.group(1).replace(",", ""))
                    except ValueError:
                        pass

            # 7. Shipping Info
            shipping_info = None
            ship_nodes = card.xpath(".//*[contains(@class, 'ybnj7e')] | .//*[contains(@class, 'fouorf')]")
            if ship_nodes:
                shipping_info = ship_nodes[0].text_content().strip()
            elif "free shipping" in raw_text.lower() or "free delivery" in raw_text.lower():
                shipping_info = "Free shipping"
            else:
                m_ship = re.search(r'([\$€£¥₹]\s*\d+(?:\.\d{2})?\s*(?:delivery|shipping))', raw_text, re.I)
                if m_ship:
                    shipping_info = m_ship.group(1).strip()

            # 8. Condition & Stock
            condition = ItemCondition.NEW
            if "refurbished" in raw_text.lower():
                condition = ItemCondition.REFURBISHED
            elif "used" in raw_text.lower() or "pre-owned" in raw_text.lower():
                condition = ItemCondition.USED

            stock = StockStatus.IN_STOCK
            if "out of stock" in raw_text.lower() or "sold out" in raw_text.lower():
                stock = StockStatus.OUT_OF_STOCK

            # 9. Promotion Badge
            badge = None
            if "sale" in raw_text.lower():
                badge = "Sale"
            elif "price drop" in raw_text.lower():
                badge = "Price drop"

            return ShoppingOffer(
                title=html_lib.unescape(title),
                merchant_name=merchant_name,
                merchant_category=category,
                direct_url=direct_url,
                original_url=link,
                price=price,
                shipping_info=shipping_info,
                rating=rating,
                review_count=review_count,
                condition=condition,
                stock_status=stock,
                thumbnail=thumbnail,
                product_id=product_id,
                badge=badge,
            )
        except Exception as e:
            logger.debug("Failed extracting shopping card: %s", e)
            return None

    @classmethod
    def _parse_with_regex(cls, html: str, currency_hint: str = "USD") -> list[ShoppingOffer]:
        """Fallback parser using regex over raw HTML."""
        offers: list[ShoppingOffer] = []
        for block_match in _CARD_CONTAINER_PATTERN.finditer(html):
            block = block_match.group(1)
            # Find link
            m_link = re.search(r'href=["\'](https?://[^"\']+|/shopping/product/[^"\']+|/url\?[^"\']+)["\']', block)
            if not m_link:
                continue
            raw_link = m_link.group(1)
            if raw_link.startswith("/"):
                raw_link = f"https://www.google.com{raw_link}"

            direct_url = URLUnwrapper.unwrap(raw_link)

            # Find price
            m_price = _PRICE_PATTERN.search(block)
            if not m_price:
                continue
            price = PriceNormalizer.parse(m_price.group(0), currency_hint=currency_hint)
            if not price:
                continue

            # Find title
            m_title = re.search(r'<h[34][^>]*>(.*?)</h[34]>', block, re.DOTALL | re.IGNORECASE)
            title = ""
            if m_title:
                title = re.sub(r'<[^>]+>', '', m_title.group(1)).strip()
            if not title:
                title = "Product Listing"

            # Find merchant
            domain = URLUnwrapper.extract_domain(direct_url)
            merchant = domain.split(".")[0].title() if domain else "Merchant"
            category = MerchantClassifier.classify(domain=domain, title=title, merchant_name=merchant)

            offers.append(
                ShoppingOffer(
                    title=html_lib.unescape(title),
                    merchant_name=merchant,
                    merchant_category=category,
                    direct_url=direct_url,
                    original_url=raw_link,
                    price=price,
                )
            )

        return offers

    @classmethod
    def parse_comparison_page(cls, html: str, product_id: str = "") -> ShoppingComparison:
        """Parses an aggregate multi-seller comparison page (/shopping/product/...)."""
        cls.check_html(html)

        title = ""
        brand = None
        m_title = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL | re.IGNORECASE)
        if m_title:
            title = re.sub(r'<[^>]+>', '', m_title.group(1)).strip()

        # Parse comparison offers
        sellers: list[ShoppingOffer] = []
        try:
            from lxml import html as lxml_html
            tree = lxml_html.fromstring(html)
            rows = tree.xpath("//tr[contains(@class, 'sh-osd__offer-row')] | //div[contains(@class, 'sh-osd__offer-row')]")
            for row in rows:
                raw_text = row.text_content()
                price_m = _PRICE_PATTERN.search(raw_text)
                if not price_m:
                    continue
                price = PriceNormalizer.parse(price_m.group(0))
                if not price:
                    continue

                links = row.xpath(".//a[@href]")
                direct_url = ""
                orig_url = ""
                if links:
                    orig_url = links[0].get("href", "")
                    if orig_url.startswith("/"):
                        orig_url = f"https://www.google.com{orig_url}"
                    direct_url = URLUnwrapper.unwrap(orig_url)

                domain = URLUnwrapper.extract_domain(direct_url)
                merchant = domain.split(".")[0].title() if domain else "Seller"

                sellers.append(
                    ShoppingOffer(
                        title=title,
                        merchant_name=merchant,
                        direct_url=direct_url,
                        original_url=orig_url,
                        price=price,
                    )
                )
        except Exception as e:
            logger.debug("Failed parsing comparison rows: %s", e)

        return ShoppingComparison(
            product_id=product_id,
            title=title,
            brand=brand,
            sellers=sellers,
        )
