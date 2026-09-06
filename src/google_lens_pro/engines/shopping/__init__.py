"""SPDX-FileCopyrightText: © 2026 Talib Kareem <taazkareem@icloud.com>
SPDX-License-Identifier: MIT

Google Shopping search engine, SERP card parser, and comparison table extractor.
"""

from .engine import ShoppingEngine
from .parser import ShoppingParser

__all__ = [
    "ShoppingEngine",
    "ShoppingParser",
]
