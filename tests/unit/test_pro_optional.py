"""The MIT core has to work when the proprietary Pro engines are absent.

These run in both trees: with the Pro engines installed they exercise the
fallback by patching the flag, and in the MIT source tree the flag is already
False.
"""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from google_lens_pro import _pro
from google_lens_pro._pro import (
    POLAR_LINKS,
    get_paywall_message,
)
from google_lens_pro.cli import cli
from google_lens_pro.models import LensSearchResult, VisualMatch


def _sample_result() -> LensSearchResult:
    return LensSearchResult(
        query_url="https://lens.google.com/search?p=1",
        visual_matches=[VisualMatch(title="Apple Watch Ultra 2", price="$799")],
    )


def test_enrichment_skipped_without_pro_engines():
    with patch.object(_pro, "AVAILABLE", False):
        assert _pro.enrich(_sample_result()).commerce is None


def test_licence_commands_exit_cleanly_without_pro_engines():
    """Commands that genuinely need the Pro engines fail with an install hint."""
    runner = CliRunner()
    with patch.object(_pro, "AVAILABLE", False):
        for args in (["pro", "status"], ["activate", "LENS_X"], ["license", "deactivate"]):
            result = runner.invoke(cli, args)
            assert result.exit_code == 1, args
            assert "pip install google-lens-pro" in result.output, args


def test_checkout_still_reachable_without_pro_engines():
    """Buying needs only public checkout links, so it must work from an MIT checkout."""
    runner = CliRunner()
    with patch.object(_pro, "AVAILABLE", False), patch("webbrowser.open"), patch("click.launch"):
        for args in (["buy"], ["upgrade"]):
            result = runner.invoke(cli, args)
            assert result.exit_code == 0, (args, result.output)
            assert "buy.polar.sh" in result.output, args


def test_cli_help_works_without_pro_engines():
    with patch.object(_pro, "AVAILABLE", False):
        assert CliRunner().invoke(cli, ["--help"]).exit_code == 0


def test_paywall_copy_ships_with_the_mit_core():
    """Checkout links and upgrade copy carry no proprietary logic, so they live MIT-side."""
    assert set(POLAR_LINKS) == {"monthly", "annual", "lifetime"}
    msg = get_paywall_message()
    assert "Google Lens Pro" in msg
    assert "https://buy.polar.sh/" in msg
    assert "AI ASSISTANT" not in msg


def test_checkout_links_are_env_overridable(monkeypatch):
    monkeypatch.setenv("POLAR_CHECKOUT_LIFETIME", "https://example.test/lifetime")
    assert "https://example.test/lifetime" in get_paywall_message()
