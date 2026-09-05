"""The MIT core has to work when the proprietary Pro engines are absent.

These run in both trees: with the Pro engines installed they exercise the
fallback by patching the flag, and in the MIT source tree the flag is already
False.
"""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from google_lens_scraper import _pro
from google_lens_scraper.cli import cli
from google_lens_scraper.models import LensSearchResult, VisualMatch


def _sample_result() -> LensSearchResult:
    return LensSearchResult(
        query_url="https://lens.google.com/search?p=1",
        visual_matches=[VisualMatch(title="Apple Watch Ultra 2", price="$799")],
    )


def test_enrichment_skipped_without_pro_engines():
    with patch.object(_pro, "AVAILABLE", False):
        assert _pro.enrich(_sample_result()).commerce is None


def test_pro_cli_commands_exit_cleanly_without_pro_engines():
    runner = CliRunner()
    with patch.object(_pro, "AVAILABLE", False):
        for args in (["upgrade"], ["buy"], ["pro", "status"]):
            result = runner.invoke(cli, args)
            assert result.exit_code == 1, args
            assert "pip install google-lens-scraper" in result.output, args


def test_cli_help_works_without_pro_engines():
    with patch.object(_pro, "AVAILABLE", False):
        assert CliRunner().invoke(cli, ["--help"]).exit_code == 0
