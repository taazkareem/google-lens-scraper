from __future__ import annotations

from typing import Any

from .core import calculate_cost
from .models import (
    BillingTier,
    GeminiCostBreakdown,
    GeminiUsageRecord,
    ModalityBreakdown,
)
from .normalizer import normalize_usage
from .registry import PricingRegistry, get_default_registry


class UsageAccumulator:
    """
    Stateful zero-drift token accumulator for multi-step agent workflows,
    pipeline executions, and multi-turn chat sessions.
    """

    def __init__(
        self,
        default_model: str = "gemini-3.7-flash",
        billing_tier: BillingTier = "unknown",
        pricing_registry: PricingRegistry | None = None,
    ) -> None:
        self.default_model = default_model
        self.default_billing_tier = billing_tier
        self.pricing_registry = pricing_registry or get_default_registry()
        self._records: list[GeminiUsageRecord] = []

    def add_call(
        self,
        response_or_usage: Any,
        model: str | None = None,
        duration_seconds: float = 0.0,
        key_tag: str | None = None,
        billing_tier: BillingTier | None = None,
        is_batch: bool = False,
        search_queries: int = 0,
    ) -> GeminiUsageRecord:
        """
        Records a single Gemini API call and accumulates its integer tokens.
        """
        record = normalize_usage(
            response_or_usage=response_or_usage,
            model=model or self.default_model,
            billing_tier=billing_tier or self.default_billing_tier,
            is_batch=is_batch,
            key_tag=key_tag,
            duration_seconds=duration_seconds,
            search_queries=search_queries,
        )
        self._records.append(record)
        return record

    def get_records(self) -> list[GeminiUsageRecord]:
        """Returns all individual normalized usage records recorded so far."""
        return list(self._records)

    def get_summary_record(self) -> GeminiUsageRecord:
        """
        Aggregates raw integer token counts across all recorded calls into a single
        unified GeminiUsageRecord, avoiding intermediate floating-point rounding drift.
        """
        if not self._records:
            return GeminiUsageRecord(
                model=self.default_model,
                billing_tier=self.default_billing_tier,
                calls_count=0,
            )

        total_prompt = sum(r.prompt_tokens for r in self._records)
        total_cached = sum(r.cached_tokens for r in self._records)
        total_output = sum(r.output_tokens for r in self._records)
        total_thinking = sum(r.thinking_tokens for r in self._records)
        total_tokens = sum(r.total_tokens for r in self._records)
        total_queries = sum(r.search_queries for r in self._records)
        total_duration = sum(r.duration_seconds for r in self._records)

        mod_text = sum(r.modality_details.text_tokens for r in self._records)
        mod_image = sum(r.modality_details.image_tokens for r in self._records)
        mod_video = sum(r.modality_details.video_tokens for r in self._records)
        mod_audio = sum(r.modality_details.audio_tokens for r in self._records)

        out_mod_text = sum(r.output_modality_details.text_tokens for r in self._records)
        out_mod_image = sum(r.output_modality_details.image_tokens for r in self._records)
        out_mod_video = sum(r.output_modality_details.video_tokens for r in self._records)
        out_mod_audio = sum(r.output_modality_details.audio_tokens for r in self._records)

        any_paid = any(r.billing_tier == "paid" for r in self._records)
        any_unknown = any(r.billing_tier == "unknown" for r in self._records)
        summary_tier: BillingTier = "paid" if any_paid else ("unknown" if any_unknown else "free")

        # If multiple models were called, tag with primary/default model
        dominant_model = self._records[0].model if len(self._records) == 1 else self.default_model

        return GeminiUsageRecord(
            model=dominant_model,
            prompt_tokens=total_prompt,
            cached_tokens=total_cached,
            output_tokens=total_output,
            thinking_tokens=total_thinking,
            total_tokens=total_tokens,
            search_queries=total_queries,
            is_batch=all(r.is_batch for r in self._records),
            billing_tier=summary_tier,
            modality_details=ModalityBreakdown(
                text_tokens=mod_text,
                image_tokens=mod_image,
                video_tokens=mod_video,
                audio_tokens=mod_audio,
            ),
            output_modality_details=ModalityBreakdown(
                text_tokens=out_mod_text,
                image_tokens=out_mod_image,
                video_tokens=out_mod_video,
                audio_tokens=out_mod_audio,
            ),
            calls_count=len(self._records),
            duration_seconds=total_duration,
        )

    def get_total_cost(self, precision: int | None = 6) -> GeminiCostBreakdown:
        """
        Computes exact total cost by aggregating raw integer tokens per model
        and computing prices on aggregated values to eliminate rounding drift.
        """
        if not self._records:
            return calculate_cost(
                0,
                model=self.default_model,
                billing_tier=self.default_billing_tier,
                pricing_registry=self.pricing_registry,
                precision=precision,
            )

        # Group records by (model, billing_tier, is_batch) to calculate exact model costs
        groups: dict[tuple, list[GeminiUsageRecord]] = {}
        for r in self._records:
            group_key = (r.model, r.billing_tier, r.is_batch)
            groups.setdefault(group_key, []).append(r)

        prompt_cost_sum = 0.0
        cached_cost_sum = 0.0
        output_cost_sum = 0.0
        thinking_cost_sum = 0.0
        grounding_cost_sum = 0.0
        total_cost_sum = 0.0
        what_if_cost_sum = 0.0

        for (model_name, b_tier, is_batch), records in groups.items():
            agg_prompt = sum(r.prompt_tokens for r in records)
            agg_cached = sum(r.cached_tokens for r in records)
            agg_output = sum(r.output_tokens for r in records)
            agg_thinking = sum(r.thinking_tokens for r in records)
            agg_total = sum(r.total_tokens for r in records)
            agg_queries = sum(r.search_queries for r in records)

            agg_mod_text = sum(r.modality_details.text_tokens for r in records)
            agg_mod_image = sum(r.modality_details.image_tokens for r in records)
            agg_mod_video = sum(r.modality_details.video_tokens for r in records)
            agg_mod_audio = sum(r.modality_details.audio_tokens for r in records)

            agg_out_mod_text = sum(r.output_modality_details.text_tokens for r in records)
            agg_out_mod_image = sum(r.output_modality_details.image_tokens for r in records)
            agg_out_mod_video = sum(r.output_modality_details.video_tokens for r in records)
            agg_out_mod_audio = sum(r.output_modality_details.audio_tokens for r in records)

            grouped_record = GeminiUsageRecord(
                model=model_name,
                prompt_tokens=agg_prompt,
                cached_tokens=agg_cached,
                output_tokens=agg_output,
                thinking_tokens=agg_thinking,
                total_tokens=agg_total,
                search_queries=agg_queries,
                is_batch=is_batch,
                billing_tier=b_tier,
                modality_details=ModalityBreakdown(
                    text_tokens=agg_mod_text,
                    image_tokens=agg_mod_image,
                    video_tokens=agg_mod_video,
                    audio_tokens=agg_mod_audio,
                ),
                output_modality_details=ModalityBreakdown(
                    text_tokens=agg_out_mod_text,
                    image_tokens=agg_out_mod_image,
                    video_tokens=agg_out_mod_video,
                    audio_tokens=agg_out_mod_audio,
                ),
            )

            # High precision unrounded cost for this group
            cost = calculate_cost(
                grouped_record,
                billing_tier=b_tier,
                pricing_registry=self.pricing_registry,
                precision=None,
            )

            prompt_cost_sum += cost.prompt_cost_usd
            cached_cost_sum += cost.cached_cost_usd
            output_cost_sum += cost.output_cost_usd
            thinking_cost_sum += cost.thinking_cost_usd
            grounding_cost_sum += cost.grounding_cost_usd
            total_cost_sum += cost.total_cost_usd
            what_if_cost_sum += cost.what_if_paid_cost_usd

        summary = self.get_summary_record()
        effective_in = (
            (prompt_cost_sum + cached_cost_sum) / summary.prompt_tokens * 1_000_000.0
            if summary.prompt_tokens > 0
            else 0.0
        )
        effective_out = (
            output_cost_sum / summary.output_tokens * 1_000_000.0
            if summary.output_tokens > 0
            else 0.0
        )

        def _round(val: float) -> float:
            return round(val, precision) if precision is not None else val

        return GeminiCostBreakdown(
            prompt_cost_usd=_round(prompt_cost_sum),
            cached_cost_usd=_round(cached_cost_sum),
            output_cost_usd=_round(output_cost_sum),
            thinking_cost_usd=_round(thinking_cost_sum),
            grounding_cost_usd=_round(grounding_cost_sum),
            total_cost_usd=_round(total_cost_sum),
            what_if_paid_cost_usd=_round(what_if_cost_sum),
            effective_input_rate_per_m=_round(effective_in),
            effective_output_rate_per_m=_round(effective_out),
            currency="USD",
        )

    def to_dict(self, precision: int | None = 6) -> dict:
        """
        Produces standardized telemetry dictionary compliant with PRD Section 7.
        """
        summary = self.get_summary_record()
        cost = self.get_total_cost(precision=precision)
        keys_used = list({r.key_tag for r in self._records if r.key_tag})

        cost_usd_dict: dict[str, Any] = {
            "prompt_uncached": cost.prompt_cost_usd,
            "prompt_cached": cost.cached_cost_usd,
            "output": cost.output_cost_usd,
            "thinking": cost.thinking_cost_usd,
            "grounding": cost.grounding_cost_usd,
            "total": cost.total_cost_usd,
        }
        if summary.billing_tier == "free":
            cost_usd_dict["what_if_paid"] = cost.what_if_paid_cost_usd
        elif summary.billing_tier == "unknown":
            cost_usd_dict["tier_notes"] = (
                "Calculated at standard Google Cloud list rates ($0.00 actual spend if using a free-tier key)"
            )

        return {
            "model": summary.model,
            "calls_count": summary.calls_count,
            "tokens": {
                "prompt": summary.prompt_tokens,
                "cached": summary.cached_tokens,
                "output": summary.output_tokens,
                "thinking": summary.thinking_tokens,
                "total": summary.total_tokens,
                "modality": {
                    "text": summary.modality_details.text_tokens,
                    "image": summary.modality_details.image_tokens,
                    "video": summary.modality_details.video_tokens,
                    "audio": summary.modality_details.audio_tokens,
                },
            },
            "cost_usd": cost_usd_dict,
            "duration_seconds": round(summary.duration_seconds, 3),
            "billing_tier": summary.billing_tier,
            "keys_used": keys_used,
        }

    def reset(self) -> None:
        """Clears all accumulated records."""
        self._records.clear()
