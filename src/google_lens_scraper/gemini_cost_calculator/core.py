from __future__ import annotations

from typing import Any, Literal

from .models import GeminiCostBreakdown
from .normalizer import normalize_usage
from .registry import PricingRegistry, get_default_registry


def calculate_cost(
    response_or_usage: Any,
    model: str | None = None,
    *,
    billing_tier: Literal["paid", "free"] = "paid",
    is_batch: bool = False,
    search_queries: int = 0,
    pricing_registry: PricingRegistry | None = None,
    precision: int | None = 6,
) -> GeminiCostBreakdown:
    """
    Computes exact cost breakdown from a Gemini API response, usage dict, token count,
    or GeminiUsageRecord.

    Args:
        response_or_usage: Raw SDK response, usage metadata dict, integer count, or GeminiUsageRecord.
        model: Model identifier override (e.g., 'gemini-3.7-flash', 'gemini-embedding-2').
        billing_tier: 'paid' (actual spend) or 'free' ($0.00 actual spend with what-if paid tracking).
        is_batch: Whether the call was executed via the 50% discount Batch API.
        search_queries: Number of Google Search Grounding queries executed.
        pricing_registry: Custom PricingRegistry instance (defaults to global singleton).
        precision: Number of decimal places to round resulting USD figures (None for raw float).

    Returns:
        GeminiCostBreakdown with itemized costs in USD.
    """
    registry = pricing_registry or get_default_registry()
    record = normalize_usage(
        response_or_usage=response_or_usage,
        model=model,
        billing_tier=billing_tier,
        is_batch=is_batch,
        search_queries=search_queries,
    )

    pricing = registry.get_model(record.model)
    batch_multiplier = 0.5 if record.is_batch else 1.0

    # 1. Embedding Model calculation
    if pricing.is_embedding:
        mb = record.modality_details
        has_breakdown = mb.total_multimodal_tokens > 0

        if has_breakdown:
            text_tokens = mb.text_tokens
            image_tokens = mb.image_tokens
            audio_tokens = mb.audio_tokens
        else:
            text_tokens = record.prompt_tokens
            image_tokens = 0
            audio_tokens = 0

        text_rate = pricing.text_embedding_rate or pricing.input_rate_base
        image_rate = pricing.image_embedding_rate or pricing.input_rate_base
        audio_rate = pricing.audio_embedding_rate or pricing.input_rate_base

        text_cost = (text_tokens * text_rate / 1_000_000.0) * batch_multiplier
        image_cost = (image_tokens * image_rate / 1_000_000.0) * batch_multiplier
        audio_cost = (audio_tokens * audio_rate / 1_000_000.0) * batch_multiplier

        paid_prompt_cost = text_cost + image_cost + audio_cost
        paid_cached_cost = 0.0
        paid_output_cost = 0.0
        paid_thinking_cost = 0.0
        paid_grounding_cost = 0.0
        paid_total = paid_prompt_cost

        effective_input_rate = (
            (paid_prompt_cost / record.prompt_tokens * 1_000_000.0)
            if record.prompt_tokens > 0
            else text_rate
        )
        effective_output_rate = 0.0

    # 2. Generation Model calculation
    else:
        # Determine tiered input and output rates
        is_extended_context = record.prompt_tokens > pricing.tier_threshold_tokens

        if is_extended_context and pricing.input_rate_tier2 is not None:
            input_rate = pricing.input_rate_tier2
        else:
            input_rate = pricing.input_rate_base

        if is_extended_context and pricing.output_rate_tier2 is not None:
            output_rate = pricing.output_rate_tier2
        else:
            output_rate = pricing.output_rate_base

        cached_rate = pricing.get_cached_read_rate()

        # Cached vs uncached prompt tokens
        uncached_prompt_tokens = max(0, record.prompt_tokens - record.cached_tokens)

        paid_prompt_cost = (uncached_prompt_tokens * input_rate / 1_000_000.0) * batch_multiplier
        paid_cached_cost = (record.cached_tokens * cached_rate / 1_000_000.0) * batch_multiplier

        # Output tokens: image-generation models (e.g. Nano Banana) bill generated
        # image tokens far above text output tokens. When the response reported an
        # output-side modality breakdown, split the cost across it; otherwise (the
        # common case for pure-text models) price output_tokens uniformly, as before.
        out_mod = record.output_modality_details
        if out_mod.total_multimodal_tokens > 0 and pricing.image_output_rate > 0:
            image_out_tokens = out_mod.image_tokens
            non_image_out_tokens = max(0, record.output_tokens - image_out_tokens)
            paid_output_cost = (
                (non_image_out_tokens * output_rate + image_out_tokens * pricing.image_output_rate)
                / 1_000_000.0
            ) * batch_multiplier
        else:
            paid_output_cost = (record.output_tokens * output_rate / 1_000_000.0) * batch_multiplier

        # Thinking tokens are billed at the candidate output generation rate
        paid_thinking_cost = (record.thinking_tokens * output_rate / 1_000_000.0) * batch_multiplier
        # Search grounding surcharge
        paid_grounding_cost = (
            record.search_queries / 1000.0
        ) * pricing.search_grounding_rate_per_1k

        paid_total = (
            paid_prompt_cost
            + paid_cached_cost
            + paid_output_cost
            + paid_thinking_cost
            + paid_grounding_cost
        )

        total_input_cost = paid_prompt_cost + paid_cached_cost
        effective_input_rate = (
            (total_input_cost / record.prompt_tokens * 1_000_000.0)
            if record.prompt_tokens > 0
            else input_rate
        )
        effective_output_rate = (
            (paid_output_cost / record.output_tokens * 1_000_000.0)
            if record.output_tokens > 0
            else output_rate
        )

    what_if_paid_cost = paid_total

    # Apply billing tier (Free vs Paid)
    if record.billing_tier == "free":
        actual_prompt_cost = 0.0
        actual_cached_cost = 0.0
        actual_output_cost = 0.0
        actual_thinking_cost = 0.0
        actual_grounding_cost = 0.0
        actual_total_cost = 0.0
    else:
        actual_prompt_cost = paid_prompt_cost
        actual_cached_cost = paid_cached_cost
        actual_output_cost = paid_output_cost
        actual_thinking_cost = paid_thinking_cost
        actual_grounding_cost = paid_grounding_cost
        actual_total_cost = paid_total

    def _round(val: float) -> float:
        return round(val, precision) if precision is not None else val

    return GeminiCostBreakdown(
        prompt_cost_usd=_round(actual_prompt_cost),
        cached_cost_usd=_round(actual_cached_cost),
        output_cost_usd=_round(actual_output_cost),
        thinking_cost_usd=_round(actual_thinking_cost),
        grounding_cost_usd=_round(actual_grounding_cost),
        total_cost_usd=_round(actual_total_cost),
        what_if_paid_cost_usd=_round(what_if_paid_cost),
        effective_input_rate_per_m=_round(effective_input_rate),
        effective_output_rate_per_m=_round(effective_output_rate),
        currency="USD",
    )
