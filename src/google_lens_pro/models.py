"""SPDX-FileCopyrightText: © 2026 Talib Kareem <taazkareem@icloud.com>
SPDX-License-Identifier: MIT

Re-export data models from modular models package for compatibility.
"""

from .models import (
    COMMERCIAL_PAGE_TYPES,
    BoundingBox,
    CandidateMatchEvaluation,
    CommerceIntelligence,
    CommerceSummary,
    DetectedObject,
    EnrichedCommerceMatch,
    GeneratedStudioAsset,
    ItemCondition,
    KnowledgeGraph,
    LensSearchResult,
    MatchRelevance,
    MerchantCategory,
    NormalizedPrice,
    PageType,
    ProductAttributes,
    ShoppingComparison,
    ShoppingOffer,
    ShoppingResult,
    StockStatus,
    VisualAnalysis,
    VisualMatch,
)

__all__ = [
    "COMMERCIAL_PAGE_TYPES",
    "BoundingBox",
    "CandidateMatchEvaluation",
    "CommerceIntelligence",
    "CommerceSummary",
    "DetectedObject",
    "EnrichedCommerceMatch",
    "GeneratedStudioAsset",
    "ItemCondition",
    "KnowledgeGraph",
    "LensSearchResult",
    "MatchRelevance",
    "MerchantCategory",
    "NormalizedPrice",
    "PageType",
    "ProductAttributes",
    "ShoppingComparison",
    "ShoppingOffer",
    "ShoppingResult",
    "StockStatus",
    "VisualAnalysis",
    "VisualMatch",
]
