"""SPDX-FileCopyrightText: © 2026 Talib Kareem <taazkareem@icloud.com>
SPDX-License-Identifier: MIT

Unified Patchright stealth browser context manager for sync and async operations.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any

from .config import (
    BROWSER_LAUNCH_ARGS,
    BROWSER_VIEWPORT,
    LensConfig,
)

logger = logging.getLogger(__name__)


@contextmanager
def browser_page(config: LensConfig) -> Iterator[Any]:
    """Yields a Playwright/Patchright page on a configured browser context synchronously."""
    from patchright.sync_api import sync_playwright

    storage_state = config.get_storage_state()
    cookies = config.get_playwright_cookies(storage_state)

    ua = config.get_user_agent()
    launch_args = list(BROWSER_LAUNCH_ARGS) + [f"--user-agent={ua}"]
    extra_headers = config.get_headers()

    with sync_playwright() as p:
        browser = None
        if config.user_data_dir:
            p_kwargs: dict[str, Any] = {
                "user_data_dir": str(Path(config.user_data_dir).resolve()),
                "executable_path": config.executable_path,
                "headless": config.headless,
                "args": launch_args,
                "user_agent": ua,
                "extra_http_headers": extra_headers,
            }
            context = p.chromium.launch_persistent_context(**p_kwargs)
            page = context.pages[0] if context.pages else context.new_page()
        elif config.cdp_url:
            browser = p.chromium.connect_over_cdp(config.cdp_url)
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.new_page()
        else:
            browser = p.chromium.launch(
                executable_path=config.executable_path,
                headless=config.headless,
                args=launch_args,
            )
            context_kwargs: dict[str, Any] = {
                "viewport": dict(BROWSER_VIEWPORT),
                "user_agent": ua,
                "extra_http_headers": extra_headers,
            }
            if storage_state:
                context_kwargs["storage_state"] = storage_state
            context = browser.new_context(**context_kwargs)
            page = context.new_page()

        if cookies and not storage_state:
            context.add_cookies(cookies)  # type: ignore[arg-type]

        try:
            yield page
        finally:
            try:
                page.close()
            except Exception:
                pass
            try:
                context.close()
            except Exception:
                pass
            if browser:
                try:
                    browser.close()
                except Exception:
                    pass


@asynccontextmanager
async def async_browser_page(config: LensConfig) -> AsyncIterator[Any]:
    """Yields a Playwright/Patchright page on a configured browser context asynchronously."""
    from patchright.async_api import async_playwright

    storage_state = config.get_storage_state()
    cookies = config.get_playwright_cookies(storage_state)

    ua = config.get_user_agent()
    launch_args = list(BROWSER_LAUNCH_ARGS) + [f"--user-agent={ua}"]
    extra_headers = config.get_headers()

    async with async_playwright() as p:
        browser = None
        if config.user_data_dir:
            p_kwargs: dict[str, Any] = {
                "user_data_dir": str(Path(config.user_data_dir).resolve()),
                "executable_path": config.executable_path,
                "headless": config.headless,
                "args": launch_args,
                "user_agent": ua,
                "extra_http_headers": extra_headers,
            }
            context = await p.chromium.launch_persistent_context(**p_kwargs)
            page = context.pages[0] if context.pages else await context.new_page()
        elif config.cdp_url:
            browser = await p.chromium.connect_over_cdp(config.cdp_url)
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await context.new_page()
        else:
            browser = await p.chromium.launch(
                executable_path=config.executable_path,
                headless=config.headless,
                args=launch_args,
            )
            context_kwargs: dict[str, Any] = {
                "viewport": dict(BROWSER_VIEWPORT),
                "user_agent": ua,
                "extra_http_headers": extra_headers,
            }
            if storage_state:
                context_kwargs["storage_state"] = storage_state
            context = await browser.new_context(**context_kwargs)
            page = await context.new_page()

        if cookies and not storage_state:
            await context.add_cookies(cookies)  # type: ignore[arg-type]

        try:
            yield page
        finally:
            try:
                await page.close()
            except Exception:
                pass
            try:
                await context.close()
            except Exception:
                pass
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
