"""SPDX-FileCopyrightText: © 2026 Talib Kareem <taazkareem@icloud.com>
SPDX-License-Identifier: MIT

Common primitives, enums, and utility data structures.
"""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Normalized bounding box coordinates (0.0 to 1.0)."""

    center_x: float = Field(default=0.5, description="Normalized horizontal center")
    center_y: float = Field(default=0.5, description="Normalized vertical center")
    width: float = Field(default=1.0, description="Normalized width")
    height: float = Field(default=1.0, description="Normalized height")
    rotation_deg: float = Field(default=0.0, description="Rotation in degrees")


class MerchantCategory(str, Enum):
    """Classification of seller / merchant domain."""

    OFFICIAL_BRAND = "official_brand"
    MAJOR_MARKETPLACE = "major_marketplace"
    RESELLER_SPECIALIST = "reseller_specialist"
    UNVERIFIED = "unverified"


class PageType(str, Enum):
    """Classification of destination page intent."""

    PRODUCT = "product"
    ARTICLE = "article"
    SOCIAL = "social"
    PORTFOLIO = "portfolio"
    MARKETPLACE = "marketplace"
    UNCATEGORIZED = "uncategorized"


COMMERCIAL_PAGE_TYPES = (PageType.PRODUCT, PageType.MARKETPLACE)


class StockStatus(str, Enum):
    """Normalized inventory availability status."""

    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    PREORDER = "preorder"
    UNKNOWN = "unknown"


class ItemCondition(str, Enum):
    """Item physical or commercial condition."""

    NEW = "new"
    USED = "used"
    REFURBISHED = "refurbished"
    UNKNOWN = "unknown"


class MatchRelevance(str, Enum):
    """Semantic relevance to the identified target product."""

    EXACT_MATCH = "exact_match"
    SIMILAR = "similar"
    REFERENCE = "reference"
    UNRELATED = "unrelated"


class NormalizedPrice(BaseModel):
    """Normalized numeric price and currency representation."""

    raw: str = Field(description="Original price string (e.g. '$24.99')")
    amount: float = Field(description="Parsed numerical price value")
    currency: str = Field(default="USD", description="Normalized ISO currency code or symbol")
