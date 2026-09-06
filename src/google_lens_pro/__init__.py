"""Google Lens Scraper & Visual Commerce Suite.

High-performance visual reverse image search, Google Shopping scraping,
and multimodal product intelligence for Python.
"""

from ._pro import AVAILABLE as PRO_AVAILABLE
from .ai_analyzer import VisualAnalyzer
from .ai_studio import StudioSynthesizer
from .async_client import AsyncGoogleLens, AsyncLensScraper
from .client import GoogleLens, LensScraper
from .config import LensConfig
from .engines.shopping.engine import ShoppingEngine
from .engines.shopping.parser import ShoppingParser
from .exceptions import (
    LensConfigurationError,
    LensError,
    LensImageError,
    LensNetworkError,
    LensParseError,
    LensRateLimitError,
    ShoppingError,
    ShoppingParseError,
    ShoppingRateLimitError,
)
from .gemini_cost_calculator import UsageAccumulator, calculate_cost
from .models import (
    BoundingBox,
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
from .pipeline.orchestrator import FusionOrchestrator
from .session import SessionManager

if PRO_AVAILABLE:
    from .commerce import (
        CommerceAggregator,
        CommerceEnricher,
        MerchantClassifier,
        PriceNormalizer,
        URLUnwrapper,
        export_commerce_to_csv,
        export_commerce_to_json,
    )
    from .license import LicenseInfo, LicenseManager, license_manager

__version__ = "0.2.0"

__all__ = [
    "__version__",
    "GoogleLens",
    "AsyncGoogleLens",
    "LensScraper",
    "AsyncLensScraper",
    "ShoppingEngine",
    "ShoppingParser",
    "FusionOrchestrator",
    "LensConfig",
    "LensSearchResult",
    "ShoppingResult",
    "ShoppingOffer",
    "ShoppingComparison",
    "VisualMatch",
    "KnowledgeGraph",
    "DetectedObject",
    "BoundingBox",
    "CommerceIntelligence",
    "CommerceSummary",
    "EnrichedCommerceMatch",
    "NormalizedPrice",
    "MatchRelevance",
    "MerchantCategory",
    "ProductAttributes",
    "VisualAnalysis",
    "GeneratedStudioAsset",
    "ItemCondition",
    "StockStatus",
    "PageType",
    "VisualAnalyzer",
    "StudioSynthesizer",
    "UsageAccumulator",
    "calculate_cost",
    "LensError",
    "LensRateLimitError",
    "LensParseError",
    "LensNetworkError",
    "LensImageError",
    "LensConfigurationError",
    "ShoppingError",
    "ShoppingParseError",
    "ShoppingRateLimitError",
    "SessionManager",
    "PRO_AVAILABLE",
]

if PRO_AVAILABLE:
    __all__ += [
        "CommerceAggregator",
        "CommerceEnricher",
        "MerchantClassifier",
        "PriceNormalizer",
        "URLUnwrapper",
        "export_commerce_to_csv",
        "export_commerce_to_json",
        "LicenseInfo",
        "LicenseManager",
        "license_manager",
    ]
