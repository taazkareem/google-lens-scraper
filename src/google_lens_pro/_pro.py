"""Optional loader for the Pro engines.

`license.py` and `commerce.py` are proprietary and ship only in the published
wheels; the MIT source tree does not carry them. Every core module that touches
Pro goes through here, so exactly one place has to cope with them being absent.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import LensSearchResult

AVAILABLE = True

try:
    from .commerce import CommerceEnricher, export_commerce_to_csv, export_commerce_to_json
    from .license import get_machine_label, license_manager
except ImportError:  # MIT source tree, or a build without the Pro engines.
    AVAILABLE = False

__all__ = [
    "AVAILABLE",
    "CommerceEnricher",
    "POLAR_LINKS",
    "export_commerce_to_csv",
    "export_commerce_to_json",
    "get_machine_label",
    "get_paywall_message",
    "license_manager",
    "enrich",
    "enrich_async",
]

# Polar Product checkout links
POLAR_LINKS = {
    "monthly": "https://buy.polar.sh/polar_cl_nVrJAfC1HXmCMV1T2l1KwcbiiM0FavN8DccGo0K1E0Q?utm_source=lens_cli&utm_medium=paywall&utm_campaign=google_lens_pro",
    "annual": "https://buy.polar.sh/polar_cl_CWQxn1LtnLUbf5alOQMUgzTIQRQUrXjk6vXXQ0d5wBx?utm_source=lens_cli&utm_medium=paywall&utm_campaign=google_lens_pro",
    "lifetime": "https://buy.polar.sh/polar_cl_LvZYm1TaDHiQof4M4DyiLjMXVnV8y7DtJkcCK21Xpc8?utm_source=lens_cli&utm_medium=paywall&utm_campaign=google_lens_pro",
}


def get_paywall_message(context: str = "tool") -> str:
    """Builds a high-converting markdown paywall message directing agents and users to Polar checkout."""
    monthly_url = os.getenv("POLAR_CHECKOUT_MONTHLY", POLAR_LINKS["monthly"])
    annual_url = os.getenv("POLAR_CHECKOUT_ANNUAL", POLAR_LINKS["annual"])
    lifetime_url = os.getenv("POLAR_CHECKOUT_LIFETIME", POLAR_LINKS["lifetime"])

    return f"""
# 🔒 Google Lens Pro — Multi-Store Pricing Intelligence Preview
**A valid Pro license key is required to unlock full 50+ store pricing fusion, direct product URL crawling, and complete dataset exports.**

> **Note:** Google Lens visual search, OCR text extraction, and Gemini 3.8 Flash multimodal vision are free (BYOK).
> Activate Pro to unlock unlimited real-time marketplace aggregation (StockX, GOAT, Flight Club, eBay, Walmart), market valuation analytics, and bulk structured export:
- **[Monthly - $19/mo]({monthly_url})** — Pay-as-you-go flexibility
- **[Annual - $99/yr (Save 55%)]({annual_url})** — Most popular for researchers & developers
- **[Lifetime - $99 (Launch Special)]({lifetime_url})** — One-time payment, unlimited forever

> **Already purchased a license?**
> Run `lens pro activate <key>` to authorize this machine!

Questions? https://github.com/taazkareem/google-lens-pro/issues
""".strip()


def enrich(
    result: LensSearchResult,
    on_progress: Any = None,
) -> LensSearchResult:
    """Attaches commerce intelligence via the Unified Fusion Pipeline (Lens + Shopping)."""
    if not AVAILABLE:
        return result

    if license_manager.validate().is_valid:
        try:
            return fuse(result, enable_shopping=True, on_progress=on_progress)
        except Exception:
            result.commerce = CommerceEnricher.process(
                result.visual_matches, is_preview=False, on_progress=on_progress
            )
            return result
    else:
        result.commerce = CommerceEnricher.process(
            result.visual_matches,
            is_preview=True,
            upgrade_message=get_paywall_message(),
            on_progress=on_progress,
        )
        return result


async def enrich_async(
    result: LensSearchResult,
    on_progress: Any = None,
) -> LensSearchResult:
    """Async twin of `enrich`: executes Unified Fusion Pipeline asynchronously."""
    if not AVAILABLE:
        return result

    if license_manager.validate().is_valid:
        try:
            return await fuse_async(
                result, enable_shopping=True, on_progress=on_progress
            )
        except Exception:
            result.commerce = await CommerceEnricher.process_async(
                result.visual_matches, is_preview=False, on_progress=on_progress
            )
            return result
    else:
        result.commerce = await CommerceEnricher.process_async(
            result.visual_matches,
            is_preview=True,
            upgrade_message=get_paywall_message(),
            on_progress=on_progress,
        )
        return result


def fuse(
    result: LensSearchResult,
    config: Any = None,
    enable_shopping: bool = True,
    on_progress: Any = None,
) -> LensSearchResult:
    """Synchronously executes the Unified Fusion pipeline (Lens + Shopping)."""
    if not AVAILABLE:
        return result
    from .commerce.enricher import _run_coroutine
    from .pipeline.orchestrator import FusionOrchestrator

    orchestrator = FusionOrchestrator(config=config)
    return _run_coroutine(
        orchestrator.fuse_async(
            lens_result=result,
            enable_shopping=enable_shopping,
            on_progress=on_progress,
        )
    )


async def fuse_async(
    result: LensSearchResult,
    config: Any = None,
    enable_shopping: bool = True,
    on_progress: Any = None,
) -> LensSearchResult:
    """Asynchronously executes the Unified Fusion pipeline (Lens + Shopping)."""
    if not AVAILABLE:
        return result
    from .pipeline.orchestrator import FusionOrchestrator

    orchestrator = FusionOrchestrator(config=config)
    return await orchestrator.fuse_async(
        lens_result=result,
        enable_shopping=enable_shopping,
        on_progress=on_progress,
    )

