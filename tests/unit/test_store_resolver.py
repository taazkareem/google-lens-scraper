"""SPDX-FileCopyrightText: © 2026 Talib Kareem <taazkareem@icloud.com>
SPDX-License-Identifier: LicenseRef-Proprietary

Unit tests for DirectStoreResolver concurrent store crawler.
"""

import pytest
from unittest.mock import AsyncMock, patch

from google_lens_pro.commerce.resolver import DirectStoreResolver
from google_lens_pro.models.commerce import EnrichedCommerceMatch
from google_lens_pro.models.common import NormalizedPrice


class MockAttrib(dict):
    pass


class MockElement:
    def __init__(self, href: str):
        self.attrib = {"href": href}


class MockPage:
    def __init__(self, status: int, links: list[str]):
        self.status = status
        self._links = [MockElement(l) for l in links]

    def css(self, selector: str):
        return self._links


@pytest.mark.asyncio
async def test_direct_store_resolver_ebay_and_lyst():
    item1 = EnrichedCommerceMatch(
        title="Nike Free RN 2018",
        merchant_name="eBay",
        direct_url="https://www.ebay.com/sch/i.html?_nkw=Nike+Free+RN+2018",
        price=NormalizedPrice(raw="$65.00", amount=65.0, currency="USD"),
    )
    item2 = EnrichedCommerceMatch(
        title="Nike Free RN Flyknit",
        merchant_name="Lyst",
        direct_url="https://www.lyst.com/search/?q=Nike+Free+RN+Flyknit",
        price=NormalizedPrice(raw="$120.00", amount=120.0, currency="USD"),
    )
    item3 = EnrichedCommerceMatch(
        title="Direct Item Already",
        merchant_name="Direct Shop",
        direct_url="https://directshop.com/products/shoe-123",
        price=NormalizedPrice(raw="$100.00", amount=100.0, currency="USD"),
    )

    async def mock_get(url, timeout=4):
        if "ebay.com" in url:
            return MockPage(200, ["https://www.ebay.com/itm/987654321?itmmeta=abc"])
        if "lyst.com" in url:
            return MockPage(200, ["/shoes/nike-free-rn-flyknit-red/"])
        return MockPage(404, [])

    with patch("google_lens_pro.commerce.resolver.AsyncFetcher") as mock_fetcher_cls:
        instance = mock_fetcher_cls.return_value
        instance.get = AsyncMock(side_effect=mock_get)

        progress_calls = []

        def on_progress(msg):
            progress_calls.append(msg)

        resolved = await DirectStoreResolver.resolve_async([item1, item2, item3], on_progress=on_progress)

        assert len(resolved) == 3
        # eBay direct item link resolved and query params cleaned
        assert resolved[0].direct_url == "https://www.ebay.com/itm/987654321"
        # Lyst relative product link resolved to full domain
        assert resolved[1].direct_url == "https://www.lyst.com/shoes/nike-free-rn-flyknit-red/"
        # Non-search URL untouched
        assert resolved[2].direct_url == "https://directshop.com/products/shoe-123"
        # Progress callback was invoked
        assert len(progress_calls) >= 2


@pytest.mark.asyncio
async def test_direct_store_resolver_timeout_fallback():
    item = EnrichedCommerceMatch(
        title="Nike Free RN 2018",
        merchant_name="eBay",
        direct_url="https://www.ebay.com/sch/i.html?_nkw=Nike+Free+RN+2018",
        price=NormalizedPrice(raw="$65.00", amount=65.0, currency="USD"),
    )

    async def mock_get_fail(url, timeout=4):
        raise TimeoutError("Connection timed out")

    with patch("google_lens_pro.commerce.resolver.AsyncFetcher") as mock_fetcher_cls:
        instance = mock_fetcher_cls.return_value
        instance.get = AsyncMock(side_effect=mock_get_fail)

        resolved = await DirectStoreResolver.resolve_async([item])
        # Gracefully retains original search URL on failure
        assert resolved[0].direct_url == "https://www.ebay.com/sch/i.html?_nkw=Nike+Free+RN+2018"
