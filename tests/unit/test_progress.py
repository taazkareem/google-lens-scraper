"""Unit tests for progress indicator reporting across client, async client, commerce, and CLI."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from click.testing import CliRunner
from rich.console import Console

from google_lens_pro.async_client import AsyncLensScraper
from google_lens_pro.cli import cli
from google_lens_pro.client import LensScraper
from google_lens_pro.commerce import CommerceEnricher
from google_lens_pro.models import (
    LensSearchResult,
    VisualMatch,
)


def _sample_search_result() -> LensSearchResult:
    return LensSearchResult(
        query_url="https://lens.google.com/test",
        visual_matches=[
            VisualMatch(
                title="Red Running Shoe",
                link="https://google.com/url?q=https://nike.com/shoe",
                source="Nike",
                price="$120.00",
                currency="USD",
            )
        ],
    )


def test_client_search_on_progress():
    """Verify that LensScraper.search invokes on_progress across stages."""
    scraper = LensScraper()
    progress_messages: list[str] = []

    with (
        patch.object(scraper, "search_image_url", return_value=_sample_search_result()),
        patch("google_lens_pro._pro.enrich") as mock_enrich,
    ):
        mock_enrich.side_effect = lambda res, on_progress=None: res

        res = scraper.search(
            "https://example.com/shoe.jpg",
            enrich=True,
            analyze=False,
            studio=False,
            on_progress=progress_messages.append,
        )

        assert res is not None
        assert len(progress_messages) >= 2
        assert any("Navigating Google Lens" in m for m in progress_messages)
        assert any("Enriching merchant pricing" in m for m in progress_messages)


def test_client_detect_on_progress():
    """Verify that LensScraper.detect invokes on_progress."""
    scraper = LensScraper()
    progress_messages: list[str] = []

    with (
        patch.object(scraper, "_resolve_to_bytes", return_value=b"fake-bytes"),
        patch.object(
            scraper.protobuf_engine,
            "process_image_bytes_sync",
            return_value={"ocr_text": "Sample Text"},
        ),
    ):
        res = scraper.detect(
            b"fake-bytes",
            on_progress=progress_messages.append,
        )

        assert res.ocr_text == "Sample Text"
        assert len(progress_messages) == 1
        assert "Extracting OCR text" in progress_messages[0]


@pytest.mark.asyncio
async def test_async_client_search_on_progress_sync_callback():
    """Verify AsyncLensScraper.search supports synchronous on_progress callbacks."""
    scraper = AsyncLensScraper()
    progress_messages: list[str] = []

    with (
        patch.object(
            scraper, "search_image_url", new=AsyncMock(return_value=_sample_search_result())
        ),
        patch("google_lens_pro._pro.enrich_async", new=AsyncMock()) as mock_enrich_async,
    ):
        mock_enrich_async.side_effect = lambda res, on_progress=None: res

        res = await scraper.search(
            "https://example.com/shoe.jpg",
            enrich=True,
            analyze=False,
            studio=False,
            on_progress=progress_messages.append,
        )

        assert res is not None
        assert any("Navigating Google Lens" in m for m in progress_messages)
        assert any("Enriching merchant pricing" in m for m in progress_messages)


@pytest.mark.asyncio
async def test_async_client_search_on_progress_async_callback():
    """Verify AsyncLensScraper.search supports async on_progress callbacks."""
    scraper = AsyncLensScraper()
    progress_messages: list[str] = []

    async def async_cb(msg: str) -> None:
        await asyncio.sleep(0.001)
        progress_messages.append(msg)

    with (
        patch.object(
            scraper, "search_image_url", new=AsyncMock(return_value=_sample_search_result())
        ),
        patch("google_lens_pro._pro.enrich_async", new=AsyncMock()) as mock_enrich_async,
    ):
        mock_enrich_async.side_effect = lambda res, on_progress=None: res

        res = await scraper.search(
            "https://example.com/shoe.jpg",
            enrich=True,
            analyze=False,
            studio=False,
            on_progress=async_cb,
        )

        assert res is not None
        assert any("Navigating Google Lens" in m for m in progress_messages)
        assert any("Enriching merchant pricing" in m for m in progress_messages)


@pytest.mark.asyncio
async def test_async_client_detect_on_progress():
    """Verify AsyncLensScraper.detect invokes on_progress."""
    scraper = AsyncLensScraper()
    progress_messages: list[str] = []

    with (
        patch.object(scraper, "_resolve_to_bytes", new=AsyncMock(return_value=b"fake-bytes")),
        patch.object(
            scraper.protobuf_engine,
            "process_image_bytes",
            new=AsyncMock(return_value={"ocr_text": "Async Sample"}),
        ),
    ):
        res = await scraper.detect(
            b"fake-bytes",
            on_progress=progress_messages.append,
        )

        assert res.ocr_text == "Async Sample"
        assert len(progress_messages) == 1
        assert "Extracting OCR text" in progress_messages[0]


@pytest.mark.asyncio
async def test_commerce_enricher_on_progress():
    """Verify CommerceEnricher.enrich_matches_deep_async reports progress."""
    progress_messages: list[str] = []
    matches = [
        VisualMatch(
            title="Test Shoe",
            link="https://example.com/shoe",
            source="Shop",
        )
    ]

    with patch(
        "google_lens_pro.commerce.ScraplingDestinationFetcher.fetch_many",
        new=AsyncMock(return_value={"https://example.com/shoe": "<html></html>"}),
    ):
        items = await CommerceEnricher.enrich_matches_deep_async(
            matches,
            max_items=1,
            on_progress=progress_messages.append,
        )

        assert len(items) == 1
        assert any("Fetching metadata" in m for m in progress_messages)
        assert any("Extracting structured" in m for m in progress_messages)


def test_cli_search_json_suppresses_progress():
    """Verify that running CLI with --json-output outputs valid JSON without progress indicators."""
    runner = CliRunner()
    with patch("google_lens_pro.cli.LensScraper.search", return_value=_sample_search_result()):
        result = runner.invoke(cli, ["search", "https://example.com/test.jpg", "--json-output"])
        assert result.exit_code == 0
        assert "https://lens.google.com/test" in result.output
        assert "Connecting to Google Lens" not in result.output


def test_cli_search_terminal_progress_invoked():
    """Verify that CLI search invokes status context when in terminal mode."""
    runner = CliRunner()

    with (
        patch(
            "google_lens_pro.cli.LensScraper.search", return_value=_sample_search_result()
        ) as mock_search,
        patch.object(Console, "is_terminal", new_callable=PropertyMock, return_value=True),
        patch("google_lens_pro.cli.stderr_console.status") as mock_status,
    ):
        mock_ctx = MagicMock()
        mock_status.return_value.__enter__.return_value = mock_ctx

        result = runner.invoke(cli, ["search", "https://example.com/test.jpg", "--no-enrich"])
        assert result.exit_code == 0
        mock_status.assert_called_once()
        assert mock_search.call_args.kwargs.get("on_progress") is not None
