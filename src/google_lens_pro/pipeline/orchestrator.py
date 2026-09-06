"""SPDX-FileCopyrightText: © 2026 Talib Kareem <taazkareem@icloud.com>
SPDX-License-Identifier: LicenseRef-Proprietary

Unified Fusion Pipeline: Orchestrates Google Lens visual search, Gemini multimodal intelligence,
and Google Shopping verified merchant offers into a comprehensive market valuation report.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Sequence
from typing import Any

from ..ai_analyzer import VisualAnalyzer, deduce_native_analysis
from ..commerce.aggregator import CommerceAggregator
from ..commerce.enricher import CommerceEnricher
from ..commerce.resolver import DirectStoreResolver
from ..core.config import LensConfig
from ..core.license import license_manager
from ..engines.shopping.engine import ShoppingEngine
from ..models.commerce import CommerceIntelligence, CommerceSummary
from ..models.lens import VisualMatch
from ..models.result import LensSearchResult
from ..models.shopping import ShoppingResult
from ..relevance import classify_match_relevance, recompute_market_summary

logger = logging.getLogger(__name__)


async def _notify_progress(on_progress: Any, msg: str) -> None:
    if on_progress is None:
        return
    res = on_progress(msg)
    if inspect.isawaitable(res):
        await res


class FusionOrchestrator:
    """Orchestrates multi-modal visual discovery and real-time Google Shopping offers."""

    def __init__(self, config: LensConfig | None = None) -> None:
        self.config = config or LensConfig()
        self.shopping_engine = ShoppingEngine(config=self.config)

    async def fuse_async(
        self,
        lens_result: LensSearchResult,
        enable_shopping: bool = True,
        on_progress: Any = None,
    ) -> LensSearchResult:
        """Executes the complete Unified Fusion pipeline on a raw LensSearchResult."""
        is_pro = license_manager.validate().is_valid

        # 1. Multi-modal AI / Native Attribute Extraction
        await _notify_progress(on_progress, "Analyzing product silhouette and visual attributes...")
        analysis = lens_result.analysis
        if analysis is None and lens_result.query_url:
            # Check if Gemini analyzer can be run
            try:
                analyzer = VisualAnalyzer(timeout=int(self.config.timeout))
                analysis = analyzer.analyze(
                    image=lens_result.query_url,
                    visual_matches=lens_result.visual_matches,
                    knowledge_graph=lens_result.knowledge_graph,
                    ocr_text=lens_result.ocr_text,
                )
            except Exception as e:
                logger.debug("Visual analyzer skipped: %s", e)

        if analysis is None:
            analysis = deduce_native_analysis(
                visual_matches=lens_result.visual_matches,
                knowledge_graph=lens_result.knowledge_graph,
                ocr_text=lens_result.ocr_text,
            )
        lens_result.analysis = analysis

        # Determine target product search query for Google Shopping
        target_product = None
        if analysis and analysis.attributes:
            brand = analysis.attributes.brand or ""
            model = analysis.attributes.model_or_name or analysis.attributes.category or ""
            if brand and not model.lower().startswith(brand.lower()):
                target_product = f"{brand} {model}".strip()
            else:
                target_product = (model or brand).strip()

        if not target_product and lens_result.knowledge_graph and lens_result.knowledge_graph.title:
            target_product = lens_result.knowledge_graph.title.strip()

        # 2. Google Shopping Scraping (if enabled and target identified)
        shopping_result: ShoppingResult | None = None
        if enable_shopping and target_product:
            try:
                await _notify_progress(
                    on_progress, f"Querying Google Shopping for verified offers on '{target_product}'..."
                )
                max_shop_items = 40 if is_pro else 5
                shopping_result = await self.shopping_engine.search_async(
                    query=target_product,
                    country=self.config.country,
                    currency=self.config.currency,
                    max_results=max_shop_items,
                    on_progress=on_progress,
                )
                lens_result.shopping = shopping_result
            except Exception as e:
                logger.warning("Google Shopping fusion search encountered error: %s", e)

        # 3. Deep Destination Enrichment of Lens Matches
        max_lens_items = None if is_pro else 1
        lens_enriched_matches = await CommerceEnricher.enrich_matches_deep_async(
            lens_result.visual_matches,
            max_items=max_lens_items,
            on_progress=on_progress,
        )

        for item in lens_enriched_matches:
            if item.relevance is None:
                item.relevance = classify_match_relevance(item, analysis)

        # 4. Multi-Source Fusion & Deduplication
        shopping_offers = shopping_result.offers if shopping_result else []
        fused_items = CommerceAggregator.fuse_matches_and_offers(
            lens_items=lens_enriched_matches,
            shopping_offers=shopping_offers,
        )

        # In preview mode, restrict total items to 1 teaser
        final_items = fused_items[:1] if not is_pro else fused_items

        # 5. Direct Store URL Crawling & SKU Link Resolution (Option C)
        if final_items:
            final_items = await DirectStoreResolver.resolve_async(
                final_items,
                on_progress=on_progress,
            )

        # 5. Compute Unified Market Summary
        summary = recompute_market_summary(
            final_items,
            CommerceSummary(
                target_product=target_product,
                total_matches=len(lens_result.visual_matches) + len(shopping_offers),
                currency=self.config.currency or "USD",
            ),
        )

        lens_result.commerce = CommerceIntelligence(
            summary=summary,
            items=final_items,
            is_preview=not is_pro,
            analysis=analysis,
        )

        await _notify_progress(
            on_progress,
            f"Fusion complete: {len(final_items)} commercial offers unified with market valuation.",
        )
        return lens_result
