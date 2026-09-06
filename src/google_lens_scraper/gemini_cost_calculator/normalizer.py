from __future__ import annotations

import contextlib
import json
from collections.abc import Sequence
from typing import Any

from .models import BillingTier, GeminiUsageRecord, ModalityBreakdown


def _get_val(obj: Any, *keys: str, default: Any = None) -> Any:
    """Helper to extract a value from an object using attribute lookup or dict key lookup."""
    for key in keys:
        if isinstance(obj, dict):
            if key in obj:
                return obj[key]
        else:
            if hasattr(obj, key):
                return getattr(obj, key)
    return default


def parse_modality_details(raw_details: Any) -> ModalityBreakdown:
    """Extracts modality breakdown (TEXT, IMAGE, VIDEO, AUDIO) from prompt_tokens_details list."""
    if not raw_details:
        return ModalityBreakdown()

    text_tokens = 0
    image_tokens = 0
    video_tokens = 0
    audio_tokens = 0

    items: Sequence[Any]
    if isinstance(raw_details, Sequence) and not isinstance(raw_details, (str, bytes)):
        items = raw_details
    else:
        items = [raw_details]

    for item in items:
        if not item:
            continue
        modality_raw = _get_val(item, "modality", "type", default="")
        modality = str(modality_raw).upper()
        count = int(_get_val(item, "token_count", "tokenCount", "count", default=0) or 0)

        if "TEXT" in modality:
            text_tokens += count
        elif "IMAGE" in modality or "PICTURE" in modality:
            image_tokens += count
        elif "VIDEO" in modality:
            video_tokens += count
        elif "AUDIO" in modality:
            audio_tokens += count
        else:
            text_tokens += count

    return ModalityBreakdown(
        text_tokens=text_tokens,
        image_tokens=image_tokens,
        video_tokens=video_tokens,
        audio_tokens=audio_tokens,
    )


def normalize_usage(
    response_or_usage: Any,
    model: str | None = None,
    billing_tier: BillingTier = "unknown",
    is_batch: bool = False,
    key_tag: str | None = None,
    duration_seconds: float = 0.0,
    search_queries: int = 0,
) -> GeminiUsageRecord:
    """
    Universal normalizer for Google Gemini API outputs, dictionaries, SDK responses,
    pre-flight token counts, and existing records.
    """
    if isinstance(response_or_usage, GeminiUsageRecord):
        # Already normalized, optionally override model or billing_tier if provided
        return GeminiUsageRecord(
            model=model or response_or_usage.model,
            prompt_tokens=response_or_usage.prompt_tokens,
            cached_tokens=response_or_usage.cached_tokens,
            output_tokens=response_or_usage.output_tokens,
            thinking_tokens=response_or_usage.thinking_tokens,
            total_tokens=response_or_usage.total_tokens,
            search_queries=search_queries or response_or_usage.search_queries,
            is_batch=is_batch or response_or_usage.is_batch,
            billing_tier=billing_tier or response_or_usage.billing_tier,
            key_tag=key_tag or response_or_usage.key_tag,
            modality_details=response_or_usage.modality_details,
            output_modality_details=response_or_usage.output_modality_details,
            calls_count=response_or_usage.calls_count,
            duration_seconds=duration_seconds or response_or_usage.duration_seconds,
        )

    # If it's a JSON string, parse it first
    if isinstance(response_or_usage, (str, bytes)):
        with contextlib.suppress(Exception):
            response_or_usage = json.loads(response_or_usage)

    # If it's an integer / float (raw token count for pre-flight estimation)
    if isinstance(response_or_usage, (int, float)):
        tokens = int(response_or_usage)
        return GeminiUsageRecord(
            model=model or "gemini-2.5-flash",
            prompt_tokens=tokens,
            cached_tokens=0,
            output_tokens=0,
            thinking_tokens=0,
            total_tokens=tokens,
            search_queries=search_queries,
            is_batch=is_batch,
            billing_tier=billing_tier,
            key_tag=key_tag,
            modality_details=ModalityBreakdown(text_tokens=tokens),
            calls_count=1,
            duration_seconds=duration_seconds,
        )

    # Detect usage metadata container
    usage = _get_val(
        response_or_usage, "usage_metadata", "usageMetadata", "usage", default=response_or_usage
    )
    extracted_model = (
        _get_val(response_or_usage, "model", "model_name", "model_version", default=model)
        or model
        or "gemini-2.5-flash"
    )

    # Extract tokens with multi-alias fallback (camelCase and snake_case)
    prompt_tokens = int(
        _get_val(
            usage,
            "prompt_token_count",
            "promptTokenCount",
            "prompt_tokens",
            "input_tokens",
            "input_token_count",
            "total_tokens",  # For count_tokens responses where prompt count is total_tokens
            "totalTokens",
            default=0,
        )
        or 0
    )

    cached_tokens = int(
        _get_val(
            usage,
            "cached_content_token_count",
            "cachedContentTokenCount",
            "cached_tokens",
            "cached_token_count",
            default=0,
        )
        or 0
    )

    output_tokens = int(
        _get_val(
            usage,
            "candidates_token_count",
            "candidatesTokenCount",
            "output_tokens",
            "output_token_count",
            "completion_tokens",
            default=0,
        )
        or 0
    )

    thinking_tokens = int(
        _get_val(
            usage,
            "thoughts_token_count",
            "thoughtsTokenCount",
            "thinking_tokens",
            "reasoning_tokens",
            default=0,
        )
        or 0
    )

    total_tokens = int(
        _get_val(
            usage,
            "total_token_count",
            "totalTokenCount",
            "total_tokens",
            default=(prompt_tokens + output_tokens + thinking_tokens),
        )
        or (prompt_tokens + output_tokens + thinking_tokens)
    )

    # Grounding / Search queries count
    extracted_search_queries = int(
        search_queries
        or _get_val(
            response_or_usage,
            "search_queries",
            "search_query_count",
            "grounding_queries",
            default=0,
        )
        or 0
    )

    # Modality breakdown (prompt/input side)
    raw_details = _get_val(
        usage,
        "prompt_tokens_details",
        "promptTokensDetails",
        "modality_details",
        "prompt_token_details",
        default=None,
    )
    modality_details = parse_modality_details(raw_details)
    if modality_details.total_multimodal_tokens == 0 and prompt_tokens > 0:
        # Default all uncached prompt tokens to text if no modality details given
        modality_details = ModalityBreakdown(text_tokens=prompt_tokens)

    # Modality breakdown (output/candidates side) — image-generation models report
    # this so generated-image tokens can be billed at their own (much higher) rate
    # instead of the uniform text output rate.
    raw_output_details = _get_val(
        usage,
        "candidates_tokens_details",
        "candidatesTokensDetails",
        default=None,
    )
    output_modality_details = parse_modality_details(raw_output_details)

    return GeminiUsageRecord(
        model=str(extracted_model),
        prompt_tokens=prompt_tokens,
        cached_tokens=cached_tokens,
        output_tokens=output_tokens,
        thinking_tokens=thinking_tokens,
        total_tokens=total_tokens,
        search_queries=extracted_search_queries,
        is_batch=is_batch,
        billing_tier=billing_tier,
        key_tag=key_tag,
        modality_details=modality_details,
        output_modality_details=output_modality_details,
        calls_count=1,
        duration_seconds=duration_seconds,
    )
