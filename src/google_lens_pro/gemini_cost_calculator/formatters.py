from __future__ import annotations

import json

from .accumulator import UsageAccumulator
from .models import GeminiCostBreakdown, GeminiUsageRecord


def to_telemetry_json(
    source: UsageAccumulator | dict,
    indent: int = 2,
) -> str:
    """Serializes usage and cost metrics to standardized JSON."""
    if isinstance(source, UsageAccumulator):
        payload = source.to_dict()
    elif isinstance(source, dict):
        payload = source
    else:
        raise TypeError(f"Unsupported source type: {type(source)}")
    return json.dumps(payload, indent=indent)


def format_cli_table(
    accumulator_or_record: UsageAccumulator | GeminiUsageRecord,
    cost: GeminiCostBreakdown | None = None,
) -> str:
    """Formats an ASCII summary table for terminal logging and CLI outputs."""
    if isinstance(accumulator_or_record, UsageAccumulator):
        summary = accumulator_or_record.get_summary_record()
        cost_breakdown = accumulator_or_record.get_total_cost()
    else:
        summary = accumulator_or_record
        if cost is None:
            raise ValueError("cost breakdown must be provided when passing a GeminiUsageRecord")
        cost_breakdown = cost

    lines = [
        "==================================================",
        f" GEMINI COST & USAGE ACCOUNTING ({summary.model})",
        "==================================================",
        f" Total Calls        : {summary.calls_count}",
        f" Billing Tier       : {summary.billing_tier.upper()}",
        f" Duration           : {summary.duration_seconds:.2f}s",
        "--------------------------------------------------",
        " TOKENS BREAKDOWN",
        f"  - Prompt Uncached : {max(0, summary.prompt_tokens - summary.cached_tokens):,}",
        f"  - Cached Read     : {summary.cached_tokens:,}",
        f"  - Output          : {summary.output_tokens:,}",
        f"  - Thinking        : {summary.thinking_tokens:,}",
        f"  - TOTAL TOKENS    : {summary.total_tokens:,}",
        "--------------------------------------------------",
        " COST BREAKDOWN (USD)",
        f"  - Prompt Uncached : ${cost_breakdown.prompt_cost_usd:.6f}",
        f"  - Cached Read     : ${cost_breakdown.cached_cost_usd:.6f}",
        f"  - Candidates Out  : ${cost_breakdown.output_cost_usd:.6f}",
        f"  - Thinking Out    : ${cost_breakdown.thinking_cost_usd:.6f}",
        f"  - Grounding       : ${cost_breakdown.grounding_cost_usd:.6f}",
        "  ------------------------------------------------",
        f"  TOTAL ACTUAL COST : ${cost_breakdown.total_cost_usd:.6f}",
        f"  WHAT-IF PAID COST : ${cost_breakdown.what_if_paid_cost_usd:.6f}",
        "==================================================",
    ]
    return "\n".join(lines)
