"""Data models for Google Lens Scraper responses using Pydantic."""

from collections.abc import Iterator
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Normalized bounding box coordinates (0.0 to 1.0)."""

    center_x: float = Field(default=0.5, description="Normalized horizontal center")
    center_y: float = Field(default=0.5, description="Normalized vertical center")
    width: float = Field(default=1.0, description="Normalized width")
    height: float = Field(default=1.0, description="Normalized height")
    rotation_deg: float = Field(default=0.0, description="Rotation in degrees")


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


class MerchantCategory(str, Enum):
    """Classification of seller / merchant domain."""

    OFFICIAL_BRAND = "official_brand"
    MAJOR_MARKETPLACE = "major_marketplace"
    RESELLER_SPECIALIST = "reseller_specialist"
    UNVERIFIED = "unverified"


class NormalizedPrice(BaseModel):
    """Normalized numeric price and currency representation."""

    raw: str = Field(description="Original price string from Google Lens (e.g. '$24.99')")
    amount: float = Field(description="Parsed numerical price value")
    currency: str = Field(default="USD", description="Normalized ISO currency code or symbol")


class EnrichedCommerceMatch(BaseModel):
    """A commercial visual match enriched with canonical URL and pricing intelligence."""

    title: str = Field(default="", description="Product or page title")
    direct_url: str = Field(
        default="",
        description="Clean, canonical destination URL (unwrapped from Google redirects and tracking)",
    )
    original_url: str = Field(default="", description="Original Google Lens destination link")
    price: NormalizedPrice | None = Field(default=None, description="Normalized price if listed")
    merchant_name: str | None = Field(default=None, description="Domain or seller name")
    merchant_category: MerchantCategory = Field(
        default=MerchantCategory.UNVERIFIED, description="Seller classification"
    )
    in_stock: bool | None = Field(default=None, description="Stock status if detected")
    thumbnail: str | None = Field(default=None, description="Thumbnail image URL")


class CommerceSummary(BaseModel):
    """Aggregated market pricing and seller analytics."""

    total_matches: int = Field(default=0, description="Total visual matches analyzed")
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
        default=None, description="Polar.sh upgrade prompt if in preview/unauthenticated mode"
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


class VisualAnalysis(BaseModel):
    """Multimodal visual intelligence extracted via Gemini 3.8 Flash."""

    summary: str = Field(default="", description="Executive visual summary and item description")
    attributes: ProductAttributes = Field(
        default_factory=ProductAttributes, description="Extracted product attributes"
    )
    resale_recommendation: str | None = Field(
        default=None, description="Resale market velocity, demand, or pricing assessment"
    )
    tags: list[str] = Field(default_factory=list, description="Relevant descriptive visual tags")


class GeneratedStudioAsset(BaseModel):
    """Synthesized 8K commercial catalog asset via Nano Banana Pro."""

    image_path: str = Field(description="Local filesystem path where synthesized image was saved")
    prompt_used: str = Field(description="Exact prompt used for generation")
    aspect_ratio: str = Field(default="1:1", description="Aspect ratio of generated asset")
    model: str = Field(
        default="models/nano-banana-pro-preview", description="Model used for synthesis"
    )


class LensSearchResult(BaseModel):
    """Structured response from a Google Lens visual search."""

    query_url: str | None = Field(default=None, description="The Google Lens search URL executed")
    search_session_id: str | None = Field(default=None, description="Google gsessionid token")
    server_session_id: str | None = Field(default=None, description="Google lsessionid token")
    ocr_text: str | None = Field(default=None, description="Full OCR text extracted from the image")
    detected_objects: list[DetectedObject] = Field(
        default_factory=list, description="Visual objects found"
    )
    visual_matches: list[VisualMatch] = Field(
        default_factory=list, description="List of matching web items"
    )
    knowledge_graph: KnowledgeGraph | None = Field(default=None, description="Knowledge Graph card")
    commerce: CommerceIntelligence | None = Field(
        default=None, description="Pro E-Commerce and Resale Arbitrage intelligence"
    )
    analysis: VisualAnalysis | None = Field(
        default=None, description="Multimodal visual intelligence via Gemini 3.8 Flash"
    )
    studio_asset: GeneratedStudioAsset | None = Field(
        default=None, description="Synthesized 8K commercial catalog asset via Nano Banana Pro"
    )
    cost: dict[str, Any] | None = Field(
        default=None, description="Detailed Gemini token usage and financial cost telemetry"
    )

    def to_dict(self) -> dict[str, Any]:
        """Serializes the result to a clean Python dictionary."""
        return self.model_dump(exclude_none=True)

    def to_json(self, indent: int = 2) -> str:
        """Serializes the result to a formatted JSON string."""
        return self.model_dump_json(indent=indent, exclude_none=True)

    def __len__(self) -> int:
        """Returns the number of visual matches."""
        return len(self.visual_matches)

    def iter_matches(self) -> Iterator[VisualMatch]:
        """Iterates over visual matches."""
        return iter(self.visual_matches)

    def __getitem__(self, index: int) -> VisualMatch:
        """Allows direct indexing into visual matches."""
        return self.visual_matches[index]
