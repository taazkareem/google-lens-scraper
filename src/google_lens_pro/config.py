"""Backwards-compatible alias for :mod:`google_lens_pro.core.config`.

The canonical configuration module moved to ``core/`` during the modular
refactor. This thin re-export keeps existing imports — and the public
``google_lens_pro.LensConfig`` export — resolving to the same objects, so
``LensConfig`` has a single identity across the package (the modular ``core``
layer was type-checking against a second, identical copy defined here).
"""

from __future__ import annotations

from .core.config import (
    BROWSER_LAUNCH_ARGS,
    BROWSER_VIEWPORT,
    CHROME_MACOS_PATH,
    DEFAULT_CLIENT_HINTS,
    DEFAULT_USER_AGENT,
    GOOGLE_COOKIE_DOMAIN,
    GOOGLE_IMAGE_UPLOAD_URL,
    GOOGLE_SHOPPING_SEARCH_URL,
    LENS_UPLOAD_BY_URL,
    LENS_UPLOAD_URL,
    NETWORK_IDLE_TIMEOUT_MS,
    RENDER_FALLBACK_MS,
    RESULTS_RENDER_TIMEOUT_MS,
    SCROLL_DISTANCE_PX,
    SCROLL_SETTLE_MS,
    UPLOAD_POLL_INTERVAL_MS,
    LensConfig,
    build_uploadbyurl_params,
    build_uploadbyurl_url,
    parse_cookie_string,
)

__all__ = [
    "BROWSER_LAUNCH_ARGS",
    "BROWSER_VIEWPORT",
    "CHROME_MACOS_PATH",
    "DEFAULT_CLIENT_HINTS",
    "DEFAULT_USER_AGENT",
    "GOOGLE_COOKIE_DOMAIN",
    "GOOGLE_IMAGE_UPLOAD_URL",
    "GOOGLE_SHOPPING_SEARCH_URL",
    "LENS_UPLOAD_BY_URL",
    "LENS_UPLOAD_URL",
    "NETWORK_IDLE_TIMEOUT_MS",
    "RENDER_FALLBACK_MS",
    "RESULTS_RENDER_TIMEOUT_MS",
    "SCROLL_DISTANCE_PX",
    "SCROLL_SETTLE_MS",
    "UPLOAD_POLL_INTERVAL_MS",
    "LensConfig",
    "build_uploadbyurl_params",
    "build_uploadbyurl_url",
    "parse_cookie_string",
]
