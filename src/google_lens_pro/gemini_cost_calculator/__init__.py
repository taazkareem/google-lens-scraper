"""
Gemini Cost Calculator
~~~~~~~~~~~~~~~~~~~~~~

A lightweight, zero-dependency financial cost & usage accounting utility
for Google Gemini API invocations.
"""

from .accumulator import UsageAccumulator
from .core import calculate_cost
from .formatters import format_cli_table, to_telemetry_json
from .models import (
    BILLING_TIERS,
    BillingTier,
    GeminiCostBreakdown,
    GeminiUsageRecord,
    ModalityBreakdown,
    ModelPricing,
)
from .normalizer import normalize_usage
from .registry import (
    DEFAULT_PRICING_CATALOG,
    PricingRegistry,
    get_default_registry,
    reset_default_registry,
)

__version__ = "1.0.0"
__all__ = [
    "calculate_cost",
    "UsageAccumulator",
    "BillingTier",
    "BILLING_TIERS",
    "PricingRegistry",
    "get_default_registry",
    "reset_default_registry",
    "DEFAULT_PRICING_CATALOG",
    "GeminiCostBreakdown",
    "GeminiUsageRecord",
    "ModalityBreakdown",
    "ModelPricing",
    "normalize_usage",
    "to_telemetry_json",
    "format_cli_table",
]
