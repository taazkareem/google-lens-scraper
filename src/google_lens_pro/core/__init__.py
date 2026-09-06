"""SPDX-FileCopyrightText: © 2026 Talib Kareem <taazkareem@icloud.com>
SPDX-License-Identifier: MIT

Core foundations: config, auth, browser management, HTTP fetcher, licensing, and exceptions.
"""

from .auth import SessionManager
from .browser import async_browser_page, browser_page
from .config import LensConfig, get_gemini_api_key, get_gemini_billing_tier
from .exceptions import (
    LensConfigurationError,
    LensError,
    LensImageError,
    LensNetworkError,
    LensParseError,
    LensRateLimitError,
    ShoppingError,
    ShoppingParseError,
    ShoppingRateLimitError,
)
from .fetcher import ConcurrentFetcher

try:
    from .license import LicenseInfo, LicenseManager, license_manager
except ImportError:  # MIT source tree — the Pro license engine is stripped.
    LicenseInfo = LicenseManager = license_manager = None  # type: ignore[assignment,misc]

__all__ = [
    "ConcurrentFetcher",
    "LensConfig",
    "LensConfigurationError",
    "LensError",
    "LensImageError",
    "LensNetworkError",
    "LensParseError",
    "LensRateLimitError",
    "LicenseInfo",
    "LicenseManager",
    "SessionManager",
    "ShoppingError",
    "ShoppingParseError",
    "ShoppingRateLimitError",
    "async_browser_page",
    "browser_page",
    "get_gemini_api_key",
    "get_gemini_billing_tier",
    "license_manager",
]
