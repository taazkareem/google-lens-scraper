from __future__ import annotations

import json
import logging
import os
from collections.abc import Sequence
from typing import Any

from .models import ModelPricing

logger = logging.getLogger(__name__)

# Default pricing catalog per 1M tokens
DEFAULT_PRICING_CATALOG: dict[str, ModelPricing] = {
    # Gemini 3.8 & 3.7 Flash & 3.x series
    "gemini-3.8-flash": ModelPricing(
        model_id="gemini-3.8-flash",
        input_rate_base=0.75,
        input_rate_tier2=0.75,
        output_rate_base=3.75,
        output_rate_tier2=3.75,
        cached_read_rate=0.075,
        tier_threshold_tokens=128000,
    ),
    "gemini-3.7-flash": ModelPricing(
        model_id="gemini-3.7-flash",
        input_rate_base=0.75,
        input_rate_tier2=0.75,
        output_rate_base=3.75,
        output_rate_tier2=3.75,
        cached_read_rate=0.075,
        tier_threshold_tokens=128000,
    ),
    "gemini-3.7-flash-thinking": ModelPricing(
        model_id="gemini-3.7-flash-thinking",
        input_rate_base=0.75,
        input_rate_tier2=0.75,
        output_rate_base=3.75,
        output_rate_tier2=3.75,
        cached_read_rate=0.075,
        tier_threshold_tokens=128000,
    ),
    "gemini-3.6-flash": ModelPricing(
        model_id="gemini-3.6-flash",
        input_rate_base=0.75,
        input_rate_tier2=0.75,
        output_rate_base=3.75,
        output_rate_tier2=3.75,
        cached_read_rate=0.075,
        tier_threshold_tokens=128000,
    ),
    "gemini-3.5-flash": ModelPricing(
        model_id="gemini-3.5-flash",
        input_rate_base=1.50,
        output_rate_base=9.00,
        cached_read_rate=0.15,
        tier_threshold_tokens=128000,
    ),
    "gemini-3.5-flash-lite": ModelPricing(
        model_id="gemini-3.5-flash-lite",
        input_rate_base=0.30,
        output_rate_base=2.50,
        cached_read_rate=0.03,
        tier_threshold_tokens=128000,
    ),
    "gemini-3.1-pro-preview": ModelPricing(
        model_id="gemini-3.1-pro-preview",
        input_rate_base=2.00,
        input_rate_tier2=4.00,
        output_rate_base=12.00,
        output_rate_tier2=12.00,
        cached_read_rate=0.50,
        tier_threshold_tokens=200000,
    ),
    # Gemini 2.5 series
    "gemini-2.5-pro": ModelPricing(
        model_id="gemini-2.5-pro",
        input_rate_base=1.25,
        input_rate_tier2=2.50,
        output_rate_base=5.00,
        output_rate_tier2=10.00,
        cached_read_rate=0.3125,
        tier_threshold_tokens=128000,
    ),
    "gemini-2.5-flash": ModelPricing(
        model_id="gemini-2.5-flash",
        input_rate_base=0.15,
        input_rate_tier2=0.30,
        output_rate_base=0.60,
        output_rate_tier2=0.60,
        cached_read_rate=0.0375,
        tier_threshold_tokens=128000,
    ),
    "gemini-2.5-flash-lite": ModelPricing(
        model_id="gemini-2.5-flash-lite",
        input_rate_base=0.10,
        output_rate_base=0.40,
        cached_read_rate=0.025,
        tier_threshold_tokens=128000,
    ),
    # Gemini 2.0 series
    "gemini-2.0-flash": ModelPricing(
        model_id="gemini-2.0-flash",
        input_rate_base=0.10,
        input_rate_tier2=0.10,
        output_rate_base=0.40,
        cached_read_rate=0.025,
        tier_threshold_tokens=128000,
    ),
    "gemini-2.0-flash-lite": ModelPricing(
        model_id="gemini-2.0-flash-lite",
        input_rate_base=0.075,
        input_rate_tier2=0.075,
        output_rate_base=0.30,
        cached_read_rate=0.0,
        tier_threshold_tokens=128000,
    ),
    # Gemini 1.5 series
    "gemini-1.5-pro": ModelPricing(
        model_id="gemini-1.5-pro",
        input_rate_base=1.25,
        input_rate_tier2=2.50,
        output_rate_base=5.00,
        cached_read_rate=0.3125,
        tier_threshold_tokens=128000,
    ),
    "gemini-1.5-flash": ModelPricing(
        model_id="gemini-1.5-flash",
        input_rate_base=0.075,
        input_rate_tier2=0.15,
        output_rate_base=0.30,
        cached_read_rate=0.01875,
        tier_threshold_tokens=128000,
    ),
    "gemini-1.5-flash-8b": ModelPricing(
        model_id="gemini-1.5-flash-8b",
        input_rate_base=0.0375,
        input_rate_tier2=0.075,
        output_rate_base=0.15,
        cached_read_rate=0.0100,
        tier_threshold_tokens=128000,
    ),
    # Image Generation Models
    # ponytail: rates from third-party aggregators (OpenRouter), not fetched from
    # Google's own pricing page directly, as of 2026-08. Re-verify if this model's
    # price gets an authoritative source.
    "nano-banana-pro-preview": ModelPricing(
        model_id="nano-banana-pro-preview",
        input_rate_base=2.00,
        output_rate_base=12.00,
        image_output_rate=120.00,
        cached_read_rate=0.0,
    ),
    # Embedding Models
    "gemini-embedding-2": ModelPricing(
        model_id="gemini-embedding-2",
        input_rate_base=0.20,
        is_embedding=True,
        text_embedding_rate=0.20,
        image_embedding_rate=0.45,
        audio_embedding_rate=6.50,
    ),
    "gemini-embedding-001": ModelPricing(
        model_id="gemini-embedding-001",
        input_rate_base=0.15,
        is_embedding=True,
        text_embedding_rate=0.15,
        image_embedding_rate=0.15,
        audio_embedding_rate=0.15,
    ),
}

DEFAULT_ALIASES: dict[str, str] = {
    # 3.7
    "gemini-3.7-flash-latest": "gemini-3.7-flash",
    "gemini-3.7-flash-001": "gemini-3.7-flash",
    "gemini-3.7-flash-preview": "gemini-3.7-flash",
    "gemini-3.7-flash-preview-02-05": "gemini-3.7-flash",
    # 2.5
    "gemini-2.5-flash-latest": "gemini-2.5-flash",
    "gemini-2.5-pro-latest": "gemini-2.5-pro",
    "gemini-2.5-flash-001": "gemini-2.5-flash",
    "gemini-2.5-pro-001": "gemini-2.5-pro",
    # 2.0
    "gemini-2.0-flash-latest": "gemini-2.0-flash",
    "gemini-2.0-flash-001": "gemini-2.0-flash",
    "gemini-2.0-flash-exp": "gemini-2.0-flash",
    # 1.5
    "gemini-1.5-flash-latest": "gemini-1.5-flash",
    "gemini-1.5-pro-latest": "gemini-1.5-pro",
    "gemini-1.5-flash-001": "gemini-1.5-flash",
    "gemini-1.5-flash-002": "gemini-1.5-flash",
    "gemini-1.5-pro-001": "gemini-1.5-pro",
    "gemini-1.5-pro-002": "gemini-1.5-pro",
    # Embeddings
    "text-embedding-004": "gemini-embedding-001",
    "embedding-001": "gemini-embedding-001",
    # Image generation
    "gemini-3-pro-image-preview": "nano-banana-pro-preview",
    "gemini-3-pro-image": "nano-banana-pro-preview",
    "nano-banana-pro": "nano-banana-pro-preview",
}

DEFAULT_FALLBACK_MODEL = "gemini-2.5-flash"


class PricingRegistry:
    """
    Registry for managing model pricing rates, aliases, and custom price overrides.
    """

    def __init__(self, fallback_model_id: str = DEFAULT_FALLBACK_MODEL) -> None:
        self._pricing: dict[str, ModelPricing] = dict(DEFAULT_PRICING_CATALOG)
        self._aliases: dict[str, str] = dict(DEFAULT_ALIASES)
        self._fallback_model_id = fallback_model_id

    def register_model(self, pricing: ModelPricing, aliases: Sequence[str] | None = None) -> None:
        """Registers or overrides a model's pricing information."""
        self._pricing[pricing.model_id] = pricing
        if aliases:
            for alias in aliases:
                self.register_alias(alias, pricing.model_id)

    def register_alias(self, alias: str, target_model: str) -> None:
        """Registers a model alias pointing to an existing registered model."""
        clean_alias = self._clean_model_name(alias)
        clean_target = self._clean_model_name(target_model)
        self._aliases[clean_alias] = clean_target

    def get_model(self, model_name: str | None) -> ModelPricing:
        """
        Retrieves the ModelPricing for a given model name.
        Handles prefixes (e.g. 'models/'), aliases, and fuzzy suffixes.
        Falls back gracefully if the model is unmapped (AC-6).
        """
        if not model_name:
            logger.warning(
                "No model specified for cost calculation; falling back to '%s'",
                self._fallback_model_id,
            )
            return self._pricing[self._fallback_model_id]

        clean_name = self._clean_model_name(model_name)

        # 1. Direct match
        if clean_name in self._pricing:
            return self._pricing[clean_name]

        # 2. Alias match
        if clean_name in self._aliases:
            target = self._aliases[clean_name]
            if target in self._pricing:
                return self._pricing[target]

        # 3. Fuzzy prefix matching (e.g., 'gemini-3.7-flash-custom' -> 'gemini-3.7-flash')
        for registered_id in sorted(self._pricing.keys(), key=len, reverse=True):
            if clean_name.startswith(registered_id):
                return self._pricing[registered_id]

        # 4. Fallback gracefully
        logger.warning(
            "Model '%s' (cleaned: '%s') not found in pricing registry. Falling back to '%s'.",
            model_name,
            clean_name,
            self._fallback_model_id,
        )
        return self._pricing.get(
            self._fallback_model_id,
            ModelPricing(
                model_id=clean_name,
                input_rate_base=0.15,
                output_rate_base=0.60,
            ),
        )

    def _clean_model_name(self, name: str) -> str:
        """Normalizes model names (lowercases, removes 'models/' prefix)."""
        name = name.strip().lower()
        if name.startswith("models/"):
            name = name[len("models/") :]
        return name

    def load_from_json(self, json_data_or_path: str) -> None:
        """Loads custom pricing overrides from a JSON string or file path."""
        data: dict[str, dict[str, Any]]
        if os.path.exists(json_data_or_path):
            with open(json_data_or_path, encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = json.loads(json_data_or_path)

        for model_id, rates in data.items():
            input_val = rates.get("input_rate_base")
            if input_val is None:
                input_val = rates.get("input", 0.0)

            output_val = rates.get("output_rate_base")
            if output_val is None:
                output_val = rates.get("output", 0.0)

            tier_tokens_val = rates.get("tier_threshold_tokens", 128000)

            pricing = ModelPricing(
                model_id=model_id,
                input_rate_base=float(input_val if input_val is not None else 0.0),
                input_rate_tier2=float(rates["input_rate_tier2"])
                if "input_rate_tier2" in rates and rates["input_rate_tier2"] is not None
                else None,
                tier_threshold_tokens=int(
                    tier_tokens_val if tier_tokens_val is not None else 128000
                ),
                output_rate_base=float(output_val if output_val is not None else 0.0),
                output_rate_tier2=float(rates["output_rate_tier2"])
                if "output_rate_tier2" in rates and rates["output_rate_tier2"] is not None
                else None,
                cached_read_rate=float(rates["cached_read_rate"])
                if "cached_read_rate" in rates and rates["cached_read_rate"] is not None
                else None,
                search_grounding_rate_per_1k=float(
                    rates.get("search_grounding_rate_per_1k") or 35.0
                ),
                is_embedding=bool(rates.get("is_embedding", False)),
                text_embedding_rate=float(rates.get("text_embedding_rate") or 0.0),
                image_embedding_rate=float(rates.get("image_embedding_rate") or 0.0),
                audio_embedding_rate=float(rates.get("audio_embedding_rate") or 0.0),
            )
            aliases = rates.get("aliases", [])
            self.register_model(pricing, aliases=aliases)

    def load_from_env(self) -> None:
        """Checks GEMINI_PRICING_CONFIG_PATH env var and loads custom config if present."""
        env_path = os.getenv("GEMINI_PRICING_CONFIG_PATH")
        if env_path and os.path.exists(env_path):
            self.load_from_json(env_path)


_GLOBAL_REGISTRY: PricingRegistry | None = None


def get_default_registry() -> PricingRegistry:
    """Returns the process-wide default PricingRegistry singleton."""
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = PricingRegistry()
        _GLOBAL_REGISTRY.load_from_env()
    return _GLOBAL_REGISTRY


def reset_default_registry() -> PricingRegistry:
    """Resets and returns a clean default PricingRegistry."""
    global _GLOBAL_REGISTRY
    _GLOBAL_REGISTRY = PricingRegistry()
    _GLOBAL_REGISTRY.load_from_env()
    return _GLOBAL_REGISTRY
