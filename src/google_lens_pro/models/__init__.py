"""SPDX-FileCopyrightText: © 2026 Talib Kareem <taazkareem@icloud.com>
SPDX-License-Identifier: MIT

Unified typed data models for Google Lens and Google Shopping.
"""

from .commerce import (
    CandidateMatchEvaluation,
    CommerceIntelligence,
    CommerceSummary,
    EnrichedCommerceMatch,
    GeneratedStudioAsset,
    ProductAttributes,
    VisualAnalysis,
)
from .common import (
    COMMERCIAL_PAGE_TYPES,
    BoundingBox,
    ItemCondition,
    MatchRelevance,
    MerchantCategory,
    NormalizedPrice,
    PageType,
    StockStatus,
)
from .lens import (
    DetectedObject,
    KnowledgeGraph,
    VisualMatch,
)
from .result import (
    LensSearchResult,
)
from .shopping import (
    ShoppingComparison,
    ShoppingOffer,
    ShoppingResult,
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
