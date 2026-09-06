"""SPDX-FileCopyrightText: © 2026 Talib Kareem <taazkareem@icloud.com>
SPDX-License-Identifier: MIT

Exceptions hierarchy for google-lens-pro.
"""

from __future__ import annotations


class LensError(Exception):
    """Base exception for all Google Lens Scraper and Google Shopping errors."""

    def __init__(
        self, message: str, status_code: int | None = None, response_body: str | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class LensRateLimitError(LensError):
    """Raised when Google blocks requests or serves a CAPTCHA / 429 /sorry/index challenge."""


class LensParseError(LensError):
    """Raised when parsing Lens visual matches or response data fails."""


class LensNetworkError(LensError):
    """Raised when an HTTP or browser network request fails."""


class LensImageError(LensError):
    """Raised when an input image cannot be read, decoded, or prepared."""


class LensConfigurationError(LensError):
    """Raised when configuration parameters or credentials are invalid."""


class ShoppingError(LensError):
    """Base exception for Google Shopping extraction errors."""


class ShoppingParseError(ShoppingError):
    """Raised when parsing Google Shopping search or product pages fails."""


class ShoppingRateLimitError(ShoppingError):
    """Raised when Google blocks Google Shopping requests."""
