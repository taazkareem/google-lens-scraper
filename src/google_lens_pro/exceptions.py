"""SPDX-FileCopyrightText: © 2026 Talib Kareem <taazkareem@icloud.com>
SPDX-License-Identifier: MIT

Exceptions hierarchy for google-lens-pro.
Re-exports from core.exceptions for top-level access.
"""

from .core.exceptions import (
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

__all__ = [
    "LensConfigurationError",
    "LensError",
    "LensImageError",
    "LensNetworkError",
    "LensParseError",
    "LensRateLimitError",
    "ShoppingError",
    "ShoppingParseError",
    "ShoppingRateLimitError",
]
