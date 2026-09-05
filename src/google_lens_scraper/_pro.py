"""Optional loader for the Pro engines.

`license.py` and `commerce.py` are proprietary and ship only in the published
wheels; the MIT source tree does not carry them. Every core module that touches
Pro goes through here, so exactly one place has to cope with them being absent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import LensSearchResult

AVAILABLE = True

try:
    from .commerce import CommerceEnricher, export_commerce_to_csv
    from .license import (
        POLAR_LINKS,
        get_machine_label,
        get_paywall_message,
        license_manager,
    )
except ImportError:  # MIT source tree, or a build without the Pro engines.
    AVAILABLE = False

__all__ = [
    "AVAILABLE",
    "CommerceEnricher",
    "POLAR_LINKS",
    "export_commerce_to_csv",
    "get_machine_label",
    "get_paywall_message",
    "license_manager",
    "enrich",
]


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
