"""SPDX-FileCopyrightText: © 2026 Talib Kareem <taazkareem@icloud.com>
SPDX-License-Identifier: MIT

Unit tests for Unified Fusion Pipeline (Lens + Shopping).
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from google_lens_pro.core.license import LicenseInfo
from google_lens_pro.models.commerce import CommerceIntelligence, EnrichedCommerceMatch
from google_lens_pro.models.common import NormalizedPrice
from google_lens_pro.models.lens import VisualMatch
from google_lens_pro.models.result import LensSearchResult
from google_lens_pro.models.shopping import ShoppingOffer, ShoppingResult
from google_lens_pro.pipeline.orchestrator import FusionOrchestrator


@pytest.fixture
def mock_lens_result():
    return LensSearchResult(
        query_url="https://lens.google.com/search?p=abc",
        visual_matches=[
            VisualMatch(
                title="Nike Dunk Low Retro White Black Panda",
                link="https://www.google.com/url?q=https://store.example.com/dunk-panda",
                source="Example Store",
            )
        ],
    )


@pytest.fixture
def mock_shopping_result():
    return ShoppingResult(
        query="Nike Dunk Low Retro White Black Panda",
        total_offers=2,
        offers=[
            ShoppingOffer(
                title="Nike Dunk Low Panda (2021)",
                merchant_name="Nike",
                direct_url="https://nike.com/dunk-panda",
                price=NormalizedPrice(amount=115.00, currency="USD", raw="$115.00"),
            ),
            ShoppingOffer(
                title="Nike Dunk Low Retro Panda",
                merchant_name="StockX",
                direct_url="https://stockx.com/nike-dunk-low-retro-white-black",
                price=NormalizedPrice(amount=108.00, currency="USD", raw="$108.00"),
            ),
        ],
    )


@pytest.mark.asyncio
async def test_fusion_orchestrator_pro_mode(mock_lens_result, mock_shopping_result):
    """Verify FusionOrchestrator unifies matches and offers when Pro license is active."""
    orchestrator = FusionOrchestrator()

    mock_pro_license = LicenseInfo(is_valid=True, status="granted", key="POLAR_VALID")

    enriched_lens_matches = [
        EnrichedCommerceMatch(
            title=mock_lens_result.visual_matches[0].title,
            direct_url="https://store.example.com/dunk-panda",
            merchant_domain="store.example.com",
            price=NormalizedPrice(amount=130.00, currency="USD", raw="$130.00"),
        )
    ]

    with (
        patch("google_lens_pro.pipeline.orchestrator.license_manager.validate", return_value=mock_pro_license),
        patch.object(orchestrator.shopping_engine, "search_async", new=AsyncMock(return_value=mock_shopping_result)),
        patch(
            "google_lens_pro.pipeline.orchestrator.CommerceEnricher.enrich_matches_deep_async",
            new=AsyncMock(return_value=enriched_lens_matches),
        ),
    ):
        result = await orchestrator.fuse_async(mock_lens_result, enable_shopping=True)

        assert result.commerce is not None
        assert result.commerce.is_preview is False
        assert result.shopping is not None

        # Expect fused items from both Lens and Shopping
        assert len(result.commerce.items) >= 2
        summary = result.commerce.summary
        assert summary is not None
        assert summary.min_price == 108.00
        assert summary.max_price == 130.00
        assert summary.best_deal is not None
        assert summary.best_deal.price.amount == 108.00


@pytest.mark.asyncio
async def test_fusion_orchestrator_preview_mode(mock_lens_result, mock_shopping_result):
    """Verify FusionOrchestrator produces preview (teaser) when Pro license is inactive."""
    orchestrator = FusionOrchestrator()

    mock_inactive_license = LicenseInfo(is_valid=False, status="missing", key="")

    with (
        patch("google_lens_pro.pipeline.orchestrator.license_manager.validate", return_value=mock_inactive_license),
        patch.object(orchestrator.shopping_engine, "search_async", new=AsyncMock(return_value=mock_shopping_result)),
        patch(
            "google_lens_pro.pipeline.orchestrator.CommerceEnricher.enrich_matches_deep_async",
            new=AsyncMock(return_value=[]),
        ),
    ):
        result = await orchestrator.fuse_async(mock_lens_result, enable_shopping=True)

        assert result.commerce is not None
        assert result.commerce.is_preview is True
        # In preview mode, items are limited to 1 teaser
        assert len(result.commerce.items) == 1
