"""SPDX-FileCopyrightText: © 2026 Talib Kareem <taazkareem@icloud.com>
SPDX-License-Identifier: MIT

High-concurrency async HTTP fetcher using Scrapling with strict timeouts and error isolation.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

# Silence noisy Scrapling logs
logging.getLogger("scrapling").disabled = True

try:
    from scrapling.fetchers import AsyncFetcher
except ImportError:
    AsyncFetcher = None  # type: ignore

logger = logging.getLogger(__name__)


class ConcurrentFetcher:
    """Coordinates concurrent async fetching of HTTP endpoints via Scrapling."""

    @classmethod
    async def fetch_one(
        cls,
        url: str,
        sem: asyncio.Semaphore | None = None,
        timeout: int = 5,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
    ) -> tuple[str, str | None]:
        """Fetches HTML for a single URL with strict timeout and fallback."""
        if AsyncFetcher is None or not url or not url.startswith("http"):
            return url, None

        async def _do_fetch() -> tuple[str, str | None]:
            try:
                fetch_kwargs: dict[str, Any] = {"timeout": timeout}
                if headers:
                    fetch_kwargs["headers"] = headers
                if cookies:
                    fetch_kwargs["cookies"] = cookies

                resp = await asyncio.wait_for(
                    AsyncFetcher.get(url, **fetch_kwargs), timeout=timeout + 1
                )
                html = resp.body.decode("utf-8", errors="replace") if resp and resp.body else None
                return url, html
            except Exception as e:
                logger.debug("Fetch failed for %s: %s", url, e)
                return url, None

        if sem:
            async with sem:
                return await _do_fetch()
        return await _do_fetch()

    @classmethod
    async def fetch_many(
        cls,
        urls: list[str],
        max_workers: int | None = None,
        timeout: int = 5,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
    ) -> dict[str, str | None]:
        """Fetches multiple URLs concurrently."""
        if AsyncFetcher is None or not urls:
            return {u: None for u in urls}

        concurrency = max_workers or min(32, (os.cpu_count() or 4) * 4)
        sem = asyncio.Semaphore(concurrency)
        unique_urls = list(dict.fromkeys(urls))
        tasks = [
            cls.fetch_one(u, sem=sem, timeout=timeout, headers=headers, cookies=cookies)
            for u in unique_urls
        ]
        results = await asyncio.gather(*tasks)
        return dict(results)
