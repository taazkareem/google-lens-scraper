"""SPDX-FileCopyrightText: © 2026 Talib Kareem <taazkareem@icloud.com>
SPDX-License-Identifier: LicenseRef-Proprietary

Data models for enriched commerce intelligence, market valuation, and visual AI analysis.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field, computed_field

from .common import (
    COMMERCIAL_PAGE_TYPES,
    ItemCondition,
    MatchRelevance,
    MerchantCategory,
    NormalizedPrice,
    PageType,
    StockStatus,
)
from .shopping import ShoppingOffer


class EnrichedCommerceMatch(BaseModel):
    """A commercial listing enriched with canonical URL and pricing intelligence."""

    title: str = Field(default="", description="Product or page title")
    direct_url: str = Field(
        default="",
        description="Clean, canonical destination URL (unwrapped from Google redirects and tracking)",
    )
    original_url: str = Field(default="", description="Original Google destination link")
    price: NormalizedPrice | None = Field(default=None, description="Normalized price if listed")
    merchant_name: str | None = Field(default=None, description="Domain or seller name")
    merchant_category: MerchantCategory | None = Field(
        default=None, description="Seller classification"
    )
    thumbnail: str | None = Field(default=None, description="Thumbnail image URL")
    match_score: int = Field(default=100, description="Visual/product match confidence score (0-100%)")
    relevance: MatchRelevance | None = Field(
        default=None,
        description="Semantic relevance of this listing to the identified target product",
    )
    relevance_reason: str | None = Field(
        default=None, description="Short explanation for the relevance classification"
    )
    page_type: PageType = Field(
        default=PageType.PRODUCT, description="Classified intent of destination page"
    )
    brand: str | None = Field(default=None, description="Identified brand or manufacturer")
    sku: str | None = Field(default=None, description="Stock Keeping Unit or GTIN/UPC product code")
    condition: ItemCondition | None = Field(
        default=None, description="Item condition (new, used, refurbished)"
    )
    stock_status: StockStatus | None = Field(
        default=None, description="Detailed inventory availability status"
    )
    primary_image_url: str | None = Field(
        default=None, description="High-resolution primary product/page image"
    )
    shipping_info: str | None = Field(
        default=None, description="Shipping or tax details if available"
    )
    source_engine: str = Field(
        default="lens", description="Origin of match ('lens' or 'shopping')"
    )

    @computed_field(description="Stock status boolean derived from stock_status, if detected")  # type: ignore[prop-decorator]
    @property
    def in_stock(self) -> bool | None:
        if self.stock_status == StockStatus.IN_STOCK:
            return True
        if self.stock_status == StockStatus.OUT_OF_STOCK:
            return False
        return None

    @classmethod
    def from_shopping_offer(cls, offer: ShoppingOffer) -> EnrichedCommerceMatch:
        """Converts a verified Google Shopping offer into an EnrichedCommerceMatch."""
        return cls(
            title=offer.title,
            direct_url=offer.direct_url,
            original_url=offer.original_url,
            price=offer.price,
            merchant_name=offer.merchant_name,
            merchant_category=offer.merchant_category,
            thumbnail=offer.thumbnail,
            match_score=98,
            relevance=MatchRelevance.EXACT_MATCH,
            relevance_reason="Verified Google Shopping product listing",
            page_type=PageType.PRODUCT,
            condition=offer.condition,
            stock_status=offer.stock_status,
            shipping_info=offer.shipping_info,
            source_engine="shopping",
        )


class CommerceSummary(BaseModel):
    """Aggregated market pricing and seller analytics."""

    target_product: str | None = Field(
        default=None, description="Identified product against which matches were evaluated"
    )
    total_matches: int = Field(default=0, description="Total matches analyzed")
    total_priced_matches: int = Field(default=0, description="Listings with detected prices")
    min_price: float | None = Field(
        default=None, description="Lowest price detected across listings"
    )
    max_price: float | None = Field(
        default=None, description="Highest price detected across listings"
    )
    avg_price: float | None = Field(default=None, description="Average price across listings")
    currency: str | None = Field(default=None, description="Dominant currency across listings")
    best_deal: EnrichedCommerceMatch | None = Field(
        default=None, description="Lowest-priced verified listing"
    )


class ProductAttributes(BaseModel):
    """Deep multimodal product attributes identified by Gemini."""

    brand: str | None = Field(default=None, description="Identified brand or manufacturer")
    model_or_name: str | None = Field(
        default=None, description="Model, silhouette, or product title"
    )
    category: str | None = Field(default=None, description="Primary product classification")
    color: str | None = Field(default=None, description="Primary colorway or finish")
    materials: list[str] = Field(default_factory=list, description="Detected materials and fabrics")
    condition_assessment: str | None = Field(
        default=None,
        description="Visual assessment of item condition (e.g., Mint, Pre-Owned, Vintage)",
    )
    key_features: list[str] = Field(
        default_factory=list, description="Key hardware, silhouette, or design features"
    )
    authenticity_markers: list[str] = Field(
        default_factory=list, description="Notable visual details relevant for authentication"
    )
    estimated_msrp_usd: float | None = Field(
        default=None, description="Estimated original retail price in USD"
    )
    confidence_score: float = Field(
        default=1.0, description="Confidence score of attribute extraction (0.0 - 1.0)"
    )


class CandidateMatchEvaluation(BaseModel):
    """Candidate evaluation produced by Gemini during visual analysis."""

    index: int = Field(description="Index of candidate match")
    relevance: MatchRelevance = Field(
        description="Relevance classification: exact_match, similar, reference, or unrelated"
    )
    reason: str | None = Field(default=None, description="Short reason for the classification")


class VisualAnalysis(BaseModel):
    """Multimodal visual intelligence extracted via Gemini."""

    summary: str = Field(default="", description="Executive visual summary and item description")
    attributes: ProductAttributes = Field(
        default_factory=ProductAttributes, description="Extracted product attributes"
    )
    match_evaluations: list[CandidateMatchEvaluation] = Field(
        default_factory=list,
        exclude=True,
        description="Internal candidate evaluations received from Gemini",
    )
    resale_recommendation: str | None = Field(
        default=None, description="Resale market velocity, demand, or pricing assessment"
    )
    tags: list[str] = Field(default_factory=list, description="Relevant descriptive visual tags")


class CommerceIntelligence(BaseModel):
    """Pro E-Commerce and Resale Arbitrage intelligence payload."""

    summary: CommerceSummary = Field(
        default_factory=CommerceSummary, description="Aggregated market pricing analytics"
    )
    items: list[EnrichedCommerceMatch] = Field(
        default_factory=list, description="All enriched product listings"
    )
    is_preview: bool = Field(
        default=False, description="True if results represent a 1-item teaser preview"
    )
    upgrade_message: str | None = Field(
        default=None, description="Polar.sh upgrade prompt if in preview mode"
    )
    analysis: VisualAnalysis | None = Field(
        default=None, description="Multimodal visual intelligence via Gemini"
    )
    cost: dict[str, Any] | None = Field(
        default=None, description="Detailed Gemini token telemetry and financial cost data"
    )

    @property
    def products(self) -> list[EnrichedCommerceMatch]:
        """Returns only commercial product and marketplace listings."""
        return [item for item in self.items if item.page_type in COMMERCIAL_PAGE_TYPES]

    @property
    def articles(self) -> list[EnrichedCommerceMatch]:
        """Returns editorial, blog, and news listings."""
        return [item for item in self.items if item.page_type == PageType.ARTICLE]

    @property
    def social(self) -> list[EnrichedCommerceMatch]:
        """Returns social media listings."""
        return [item for item in self.items if item.page_type == PageType.SOCIAL]


class GeneratedStudioAsset(BaseModel):
    """Synthesized 8K commercial catalog asset via Nano Banana Pro."""

    image_path: str = Field(description="Local filesystem path where synthesized image was saved")
    prompt_used: str = Field(description="Exact prompt used for generation")
    aspect_ratio: str = Field(default="1:1", description="Aspect ratio of generated asset")
    model: str = Field(
        default="models/nano-banana-pro-preview", description="Model used for synthesis"
    )
