"""SPDX-FileCopyrightText: © 2026 Talib Kareem <taazkareem@icloud.com>
SPDX-License-Identifier: MIT

High-performance Google Shopping scraper supporting fast HTTP and stealth browser fallback.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import inspect
import logging
from typing import Any
from urllib.parse import urlencode

from ...commerce.enricher import _run_coroutine
from ...core.browser import async_browser_page, browser_page
from ...core.config import GOOGLE_SHOPPING_SEARCH_URL, LensConfig
from ...core.exceptions import ShoppingError, ShoppingRateLimitError
from ...core.fetcher import ConcurrentFetcher
from ...models.shopping import ShoppingComparison, ShoppingResult
from .parser import ShoppingParser

logger = logging.getLogger(__name__)


async def _notify_progress(on_progress: Any, msg: str) -> None:
    if on_progress is None:
        return
    res = on_progress(msg)
    if inspect.isawaitable(res):
        await res


class ShoppingEngine:
    """Google Shopping search engine with sub-second HTTP retrieval and stealth browser fallback."""

    def __init__(self, config: LensConfig | None = None, **kwargs: Any) -> None:
        self.config = config or LensConfig(**kwargs)

    def _build_search_url(self, query: str, country: str | None = None, currency: str | None = None) -> str:
        """Builds Google Shopping search URL with udm=28 and regional parameters."""
        gl = (country or self.config.country or "US").upper()
        hl = self.config.language or "en"
        params = {
            "q": query,
            "udm": "28",  # Google Shopping tab
            "gl": gl,
            "hl": hl,
        }
        return f"{GOOGLE_SHOPPING_SEARCH_URL}?{urlencode(params)}"

    async def search_async(
        self,
        query: str,
        country: str | None = None,
        currency: str | None = None,
        deep: bool = False,
        max_results: int = 40,
        on_progress: Any = None,
    ) -> ShoppingResult:
        """Asynchronously scrapes Google Shopping for real-time merchant offers."""
        clean_query = query.strip()
        if not clean_query:
            raise ShoppingError("Query string cannot be empty.")

        target_country = country or self.config.country or "US"
        target_currency = currency or self.config.currency or "USD"
        search_url = self._build_search_url(clean_query, target_country, target_currency)

        await _notify_progress(on_progress, f"Searching Google Shopping for '{clean_query}'...")

        headers = self.config.get_headers()
        cookies = self.config.get_httpx_cookies()

        # 1. Fast path: Scrapling high-speed HTTP fetch
        _, html = await ConcurrentFetcher.fetch_one(
            search_url,
            timeout=int(self.config.timeout),
            headers=headers,
            cookies=cookies,
        )

        needs_browser = False
        if not html:
            needs_browser = True
        else:
            try:
                ShoppingParser.check_html(html)
            except ShoppingRateLimitError:
                logger.info("Google Shopping HTTP fetch triggered challenge, falling back to stealth browser...")
                needs_browser = True

        # 2. Stealth browser fallback (Patchright)
        if needs_browser:
            await _notify_progress(on_progress, "Engaging stealth browser for Google Shopping clearance...")
            async with async_browser_page(self.config) as page:
                await page.goto(search_url, wait_until="domcontentloaded", timeout=int(self.config.timeout * 1000))
                # Settle for 1.5s to ensure dynamic cards render
                await page.wait_for_timeout(1500)
                html = await page.content()

        result = ShoppingParser.parse_serp(
            html=html or "",
            query=clean_query,
            currency_hint=target_currency,
        )

        if max_results and len(result.offers) > max_results:
            result.offers = result.offers[:max_results]
            result.total_offers = len(result.offers)

        # 3. Optional Deep comparative page extraction (/shopping/product/...)
        if deep and result.offers:
            await _notify_progress(on_progress, "Deep scraping multi-seller comparison tables...")
            comparisons: list[ShoppingComparison] = []
            for offer in result.offers[:3]:  # Top 3 products
                if offer.product_id:
                    comp_url = f"https://www.google.com/shopping/product/{offer.product_id}?gl={target_country}&hl={self.config.language}"
                    _, comp_html = await ConcurrentFetcher.fetch_one(comp_url, timeout=5, headers=headers, cookies=cookies)
                    if comp_html:
                        comp = ShoppingParser.parse_comparison_page(comp_html, product_id=offer.product_id)
                        if comp.sellers:
                            comparisons.append(comp)
            result.comparisons = comparisons

        await _notify_progress(on_progress, f"Extracted {len(result.offers)} verified Google Shopping offers.")
        return result

    def search(
        self,
        query: str,
        country: str | None = None,
        currency: str | None = None,
        deep: bool = False,
        max_results: int = 40,
        on_progress: Any = None,
    ) -> ShoppingResult:
        """Synchronously scrapes Google Shopping for real-time merchant offers."""
        return _run_coroutine(
            self.search_async(
                query=query,
                country=country,
                currency=currency,
                deep=deep,
                max_results=max_results,
                on_progress=on_progress,
            )
        )
