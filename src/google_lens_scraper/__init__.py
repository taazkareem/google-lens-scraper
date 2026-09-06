"""Google Lens Scraper - Fast reverse-engineered visual matches and OCR scraper."""

from ._pro import AVAILABLE as PRO_AVAILABLE
from .ai_analyzer import VisualAnalyzer
from .ai_studio import StudioSynthesizer
from .async_client import AsyncLensScraper
from .client import LensScraper
from .config import LensConfig
from .exceptions import (
    LensConfigurationError,
    LensError,
    LensImageError,
    LensNetworkError,
    LensParseError,
    LensRateLimitError,
)
from .gemini_cost_calculator import UsageAccumulator, calculate_cost
from .models import (
    BoundingBox,
    CommerceIntelligence,
    CommerceSummary,
    DetectedObject,
    EnrichedCommerceMatch,
    GeneratedStudioAsset,
    KnowledgeGraph,
    LensSearchResult,
    MatchRelevance,
    MerchantCategory,
    NormalizedPrice,
    ProductAttributes,
    VisualAnalysis,
    VisualMatch,
)
from .session import SessionManager

if PRO_AVAILABLE:
    from .commerce import CommerceEnricher, export_commerce_to_csv, export_commerce_to_json
    from .license import LicenseInfo, LicenseManager, license_manager

__version__ = "0.1.4"

__all__ = [
    "__version__",
    "LensScraper",
    "AsyncLensScraper",
    "LensConfig",
    "LensSearchResult",
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
    "SessionManager",
    "PRO_AVAILABLE",
]

if PRO_AVAILABLE:
    __all__ += [
        "CommerceEnricher",
        "export_commerce_to_csv",
        "export_commerce_to_json",
        "LicenseInfo",
        "LicenseManager",
        "license_manager",
    ]
