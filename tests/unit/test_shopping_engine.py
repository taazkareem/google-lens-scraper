"""SPDX-FileCopyrightText: © 2026 Talib Kareem <taazkareem@icloud.com>
SPDX-License-Identifier: MIT

Unit tests for Google Shopping Scraping Engine.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from google_lens_pro.core.config import LensConfig
from google_lens_pro.core.exceptions import ShoppingError
from google_lens_pro.engines.shopping.engine import ShoppingEngine
from google_lens_pro.models.shopping import ShoppingOffer, ShoppingResult
from google_lens_pro.models.common import NormalizedPrice


@pytest.fixture
def mock_shopping_html():
    return """
    <html>
      <div class="sh-dgr__content">
        <h3>Sony WH-1000XM5</h3>
        <a href="https://www.google.com/url?q=https://bestbuy.com/headphones"><span>$349.99</span></a>
        <div>Best Buy</div>
      </div>
    </html>
    """


def test_build_search_url():
    """Verify URL construction with regional and language query parameters."""
    engine = ShoppingEngine(LensConfig(country="uk", currency="GBP", language="en-GB"))
    url = engine._build_search_url("Sony Headphones", country="GB", currency="GBP")

    assert "https://www.google.com/search?" in url
    assert "q=Sony+Headphones" in url
    assert "udm=28" in url
    assert "gl=GB" in url


@pytest.mark.asyncio
async def test_search_async_empty_query():
    """Verify empty query raises ShoppingError."""
    engine = ShoppingEngine()
    with pytest.raises(ShoppingError, match="cannot be empty"):
        await engine.search_async("   ")


@pytest.mark.asyncio
async def test_search_async_fast_path(mock_shopping_html):
    """Verify fast-path HTTP fetch without engaging browser."""
    engine = ShoppingEngine()

    with patch(
        "google_lens_pro.core.fetcher.ConcurrentFetcher.fetch_one",
        new=AsyncMock(return_value=("https://google.com/search", mock_shopping_html)),
    ):
        result = await engine.search_async("Sony WH-1000XM5")

        assert isinstance(result, ShoppingResult)
        assert result.query == "Sony WH-1000XM5"
        assert len(result.offers) == 1
        assert result.offers[0].price.amount == 349.99


@pytest.mark.asyncio
async def test_search_async_browser_fallback(mock_shopping_html):
    """Verify fallback to stealth browser when rate limit challenge occurs."""
    engine = ShoppingEngine()

    mock_page = AsyncMock()
    mock_page.content = AsyncMock(return_value=mock_shopping_html)
    mock_page.goto = AsyncMock()
    mock_page.wait_for_timeout = AsyncMock()

    class MockAsyncBrowserPage:
        async def __aenter__(self):
            return mock_page

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with (
        patch(
            "google_lens_pro.core.fetcher.ConcurrentFetcher.fetch_one",
            new=AsyncMock(return_value=("https://google.com/search", "<html>sorry/index</html>")),
        ),
        patch(
            "google_lens_pro.engines.shopping.engine.async_browser_page",
            return_value=MockAsyncBrowserPage(),
        ),
    ):
        result = await engine.search_async("Sony WH-1000XM5")
        assert len(result.offers) == 1
        assert mock_page.goto.called


def test_search_sync_wrapper(mock_shopping_html):
    """Verify synchronous search wrapper works seamlessly."""
    engine = ShoppingEngine()

    with patch(
        "google_lens_pro.core.fetcher.ConcurrentFetcher.fetch_one",
        new=AsyncMock(return_value=("https://google.com/search", mock_shopping_html)),
    ):
        result = engine.search("Sony WH-1000XM5")
        assert isinstance(result, ShoppingResult)
        assert len(result.offers) == 1
