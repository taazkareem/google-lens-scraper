"""Optional loader for the Pro engines.

`license.py` and `commerce.py` are proprietary and ship only in the published
wheels; the MIT source tree does not carry them. Every core module that touches
Pro goes through here, so exactly one place has to cope with them being absent.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

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
    "monthly": "https://buy.polar.sh/polar_cl_nVrJAfC1HXmCMV1T2l1KwcbiiM0FavN8DccGo0K1E0Q?utm_source=lens_cli&utm_medium=paywall&utm_campaign=google_lens_scraper",
    "annual": "https://buy.polar.sh/polar_cl_CWQxn1LtnLUbf5alOQMUgzTIQRQUrXjk6vXXQ0d5wBx?utm_source=lens_cli&utm_medium=paywall&utm_campaign=google_lens_scraper",
    "lifetime": "https://buy.polar.sh/polar_cl_LvZYm1TaDHiQof4M4DyiLjMXVnV8y7DtJkcCK21Xpc8?utm_source=lens_cli&utm_medium=paywall&utm_campaign=google_lens_scraper",
}


def get_paywall_message(context: str = "tool") -> str:
    """Builds a high-converting markdown paywall message directing agents and users to Polar checkout."""
    monthly_url = os.getenv("POLAR_CHECKOUT_MONTHLY", POLAR_LINKS["monthly"])
    annual_url = os.getenv("POLAR_CHECKOUT_ANNUAL", POLAR_LINKS["annual"])
    lifetime_url = os.getenv("POLAR_CHECKOUT_LIFETIME", POLAR_LINKS["lifetime"])

    return f"""
# 🔒 Google Lens Pro — Commercial Intelligence Preview
**A valid license key is required to unlock full pricing analytics and clean direct merchant URLs.**

This is a Pro feature of Google Lens Scraper. To unlock unlimited e-commerce intelligence, normalized prices, best-deal ranking, and CSV exports across all your searches:
- **[Monthly - $19/mo]({monthly_url})** — Pay-as-you-go flexibility
- **[Annual - $99/yr (Save 55%)]({annual_url})** — Most popular for researchers & developers
- **[Lifetime - $99 (Launch Special)]({lifetime_url})** — One-time payment, unlimited forever

> **Already purchased a license?**
> Run `google-lens pro activate <key>` to authorize this machine!

Questions? https://github.com/taazkareem/google-lens-scraper/issues
""".strip()


def enrich(result: LensSearchResult) -> LensSearchResult:
    """Attaches commerce intelligence, gated on the Polar license. No-op without the Pro engines."""
    if not AVAILABLE:
        return result

    if license_manager.validate().is_valid:
        result.commerce = CommerceEnricher.process(result.visual_matches, is_preview=False)
    else:
        result.commerce = CommerceEnricher.process(
            result.visual_matches,
            is_preview=True,
            upgrade_message=get_paywall_message(),
        )
    return result


async def enrich_async(result: LensSearchResult) -> LensSearchResult:
    """Async twin of `enrich`: awaits enrichment directly instead of blocking the event loop."""
    if not AVAILABLE:
        return result

    if license_manager.validate().is_valid:
        result.commerce = await CommerceEnricher.process_async(result.visual_matches, is_preview=False)
    else:
        result.commerce = await CommerceEnricher.process_async(
            result.visual_matches,
            is_preview=True,
            upgrade_message=get_paywall_message(),
        )
    return result
