from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, get_args

BillingTier = Literal["paid", "free", "unknown"]
BILLING_TIERS: tuple[str, ...] = get_args(BillingTier)


@dataclass(frozen=True)
class ModalityBreakdown:
    """Breakdown of prompt or input tokens by modality."""

    text_tokens: int = 0
    image_tokens: int = 0
    video_tokens: int = 0
    audio_tokens: int = 0

    @property
    def total_multimodal_tokens(self) -> int:
        return self.text_tokens + self.image_tokens + self.video_tokens + self.audio_tokens


@dataclass
class GeminiUsageRecord:
    """Normalized usage container representing one or more Gemini API calls."""

    model: str
    prompt_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    total_tokens: int = 0
    search_queries: int = 0
    is_batch: bool = False
    billing_tier: BillingTier = "unknown"
    key_tag: str | None = None
    modality_details: ModalityBreakdown = field(default_factory=ModalityBreakdown)
    # Breakdown of output_tokens by modality (e.g. image-generation models bill
    # generated-image tokens at a steep premium over text output tokens). Empty
    # when the SDK response reports no candidates-side modality breakdown, in
    # which case output_tokens is priced uniformly at output_rate_base as before.
    output_modality_details: ModalityBreakdown = field(default_factory=ModalityBreakdown)
    calls_count: int = 1
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class GeminiCostBreakdown:
    """Detailed itemized cost calculation result in USD."""

    prompt_cost_usd: float
    cached_cost_usd: float
    output_cost_usd: float
    thinking_cost_usd: float
    grounding_cost_usd: float
    total_cost_usd: float
    what_if_paid_cost_usd: float
    effective_input_rate_per_m: float
    effective_output_rate_per_m: float
    currency: str = "USD"


@dataclass(frozen=True)
class ModelPricing:
    """
    Pricing specification for a Gemini model.
    All rates are expressed in USD per 1,000,000 (1M) tokens unless otherwise noted.
    """

    model_id: str
    input_rate_base: float
    input_rate_tier2: float | None = None
    tier_threshold_tokens: int = 128000
    output_rate_base: float = 0.0
    output_rate_tier2: float | None = None
    cached_read_rate: float | None = None
    search_grounding_rate_per_1k: float = 35.0
    is_embedding: bool = False
    text_embedding_rate: float = 0.0
    image_embedding_rate: float = 0.0
    audio_embedding_rate: float = 0.0
    # Premium rate for generated-image output tokens (image-generation models like
    # Nano Banana bill these far above text output tokens). 0.0 means "not set" —
    # falls back to output_rate_base so non-image-output models are unaffected.
    image_output_rate: float = 0.0

    def get_cached_read_rate(self) -> float:
        """Returns the cached read rate (defaults to 25% of input base rate if not explicitly set)."""
        if self.cached_read_rate is not None:
            return self.cached_read_rate
        return self.input_rate_base * 0.25
