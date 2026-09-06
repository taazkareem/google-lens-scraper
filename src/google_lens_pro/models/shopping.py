"""SPDX-FileCopyrightText: © 2026 Talib Kareem <taazkareem@icloud.com>
SPDX-License-Identifier: MIT

Data models for Google Shopping search results, store offers, and comparison pages.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from .common import ItemCondition, MerchantCategory, NormalizedPrice, StockStatus


class ShoppingOffer(BaseModel):
    """A verified merchant offer from Google Shopping."""

    title: str = Field(default="", description="Product title on merchant site")
    merchant_name: str = Field(default="", description="Store or seller name")
    merchant_category: MerchantCategory | None = Field(
        default=None, description="Seller classification (official brand, marketplace, reseller)"
    )
    direct_url: str = Field(default="", description="Clean direct merchant store URL")
    original_url: str = Field(default="", description="Google Shopping link or redirect")
    price: NormalizedPrice = Field(description="Active offer price")
    original_price: NormalizedPrice | None = Field(
        default=None, description="Original MSRP or pre-discount price"
    )
    shipping_info: str | None = Field(default=None, description="Shipping cost or delivery terms")
    rating: float | None = Field(default=None, description="Product or seller star rating (1.0-5.0)")
    review_count: int | None = Field(default=None, description="Total review count")
    condition: ItemCondition | None = Field(default=ItemCondition.NEW, description="Item condition")
    stock_status: StockStatus | None = Field(
        default=StockStatus.IN_STOCK, description="Inventory availability status"
    )
    thumbnail: str | None = Field(default=None, description="Product image thumbnail URL")
    product_id: str | None = Field(
        default=None, description="Google Shopping product cluster ID if present"
    )
    badge: str | None = Field(default=None, description="Promotion tag (e.g. Sale, Price drop)")


class ShoppingComparison(BaseModel):
    """Aggregate multi-seller comparison for a single Google Shopping product."""

    product_id: str = Field(description="Google Shopping product ID")
    title: str = Field(default="", description="Canonical product name")
    brand: str | None = Field(default=None, description="Product manufacturer")
    gtin: str | None = Field(default=None, description="Global Trade Item Number / UPC / EAN")
    description: str | None = Field(default=None, description="Product description")
    features: list[str] = Field(default_factory=list, description="Key specifications")
    sellers: list[ShoppingOffer] = Field(
        default_factory=list, description="All merchants offering this exact item"
    )


class ShoppingResult(BaseModel):
    """Structured response from a Google Shopping search."""

    query: str = Field(description="Search query string")
    total_offers: int = Field(default=0, description="Total merchant offers found")
    offers: list[ShoppingOffer] = Field(
        default_factory=list, description="List of verified merchant offers"
    )
    comparisons: list[ShoppingComparison] = Field(
        default_factory=list, description="Deep multi-seller comparisons if requested"
    )
    min_price: float | None = Field(default=None, description="Lowest price detected")
    max_price: float | None = Field(default=None, description="Highest price detected")
    avg_price: float | None = Field(default=None, description="Average price detected")
    currency: str | None = Field(default="USD", description="Dominant currency")
    best_deal: ShoppingOffer | None = Field(
        default=None, description="Lowest-priced verified in-stock offer"
    )

    def to_dict(self) -> dict[str, Any]:
        """Serializes response to clean dictionary."""
        return self.model_dump(exclude_none=True)

    def to_json(self, indent: int = 2) -> str:
        """Serializes response to formatted JSON string."""
        return self.model_dump_json(indent=indent, exclude_none=True)
