"""SPDX-FileCopyrightText: © 2026 Talib Kareem <taazkareem@icloud.com>
SPDX-License-Identifier: MIT

Google Lens visual search and object detection models.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .common import BoundingBox


class DetectedObject(BaseModel):
    """Object detected in an image by Google Lens."""

    id: str = Field(default="", description="Internal Google object ID")
    bounding_box: BoundingBox | None = Field(default=None, description="Object bounds")
    is_full_image: bool = Field(default=False, description="True if object represents full image")


class VisualMatch(BaseModel):
    """A visual match item from Google Lens search results."""

    title: str = Field(default="", description="Title of the matching page or product")
    link: str = Field(default="", description="Direct destination URL of the matched web page")
    thumbnail: str | None = Field(default=None, description="Google CDN thumbnail image URL")
    source: str | None = Field(
        default=None, description="Publisher or domain name (e.g. Amazon, Wikipedia)"
    )
    source_icon: str | None = Field(default=None, description="Publisher favicon or logo URL")
    price: str | None = Field(default=None, description="Product price if shopping listing")
    currency: str | None = Field(default=None, description="Currency symbol or code (e.g. $, USD)")
    in_stock: bool | None = Field(default=None, description="Stock status if available")


class KnowledgeGraph(BaseModel):
    """Knowledge Graph entity identified by Google Lens."""

    title: str | None = Field(default=None, description="Identified entity name")
    subtitle: str | None = Field(default=None, description="Entity classification or subtitle")
    description: str | None = Field(default=None, description="Short entity summary")
    thumbnail: str | None = Field(default=None, description="Entity image thumbnail URL")
