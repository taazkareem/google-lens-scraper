"""Unit tests for Gemini 3.8 Flash visual intelligence, Nano Banana Pro studio synthesis, and cost calculator integration."""

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from google_lens_scraper import PRO_AVAILABLE
from google_lens_scraper.ai_analyzer import VisualAnalyzer
from google_lens_scraper.ai_studio import StudioSynthesizer
from google_lens_scraper.gemini_cost_calculator import UsageAccumulator, calculate_cost
from google_lens_scraper.models import (
    GeneratedStudioAsset,
    LensSearchResult,
    ProductAttributes,
    VisualAnalysis,
    VisualMatch,
)

pro_only = pytest.mark.skipif(not PRO_AVAILABLE, reason="Pro engines not installed")


def _create_sample_image() -> Image.Image:
    return Image.new("RGB", (100, 100), color="red")


def _create_sample_image_bytes() -> bytes:
    img = _create_sample_image()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestVisualAnalyzer:
    def test_analyzer_not_available_without_api_key(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        analyzer = VisualAnalyzer(api_key=None)
        assert not analyzer.is_available
        assert analyzer.analyze(_create_sample_image()) is None

    def test_analyzer_zero_key_native_deduction(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        analyzer = VisualAnalyzer(api_key=None)
        assert not analyzer.is_available
        matches = [VisualMatch(title="Nike Free RN Flyknit 2017 - 880843 006 | GOAT", price="$120")]
        res = analyzer.analyze(_create_sample_image(), visual_matches=matches)
        assert res is not None
        assert res.attributes.brand == "Nike"
        assert "Nike Free RN Flyknit 2017" in res.attributes.model_or_name
        assert res.attributes.confidence_score == 0.85

    def test_analyzer_successful_generation(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        accumulator = UsageAccumulator()
        analyzer = VisualAnalyzer(api_key="test-key", accumulator=accumulator)
        assert analyzer.is_available

        sample_analysis = VisualAnalysis(
            summary="Nike Air Jordan 1 Retro High OG in Chicago colorway.",
            attributes=ProductAttributes(
                brand="Nike",
                model_or_name="Air Jordan 1 Retro High OG",
                category="Footwear / Sneakers",
                color="Varsity Red / White / Black",
                materials=["Full-grain leather", "Rubber cupsole"],
                condition_assessment="Deadstock / Brand New",
                key_features=["Wings logo on collar", "Nike Air tongue tag", "Perforated toe box"],
                authenticity_markers=[
                    "Hourglass heel shape",
                    "Clean edge paint",
                    "Crisp swoosh tip",
                ],
                estimated_msrp_usd=180.00,
                confidence_score=0.98,
            ),
            resale_recommendation="High market liquidity. Premium resale spread on StockX / GOAT.",
            tags=["sneakers", "jordan 1", "chicago", "basketball", "streetwear"],
        )

        mock_response = MagicMock()
        mock_response.parsed = sample_analysis
        mock_response.usage_metadata.prompt_token_count = 500
        mock_response.usage_metadata.candidates_token_count = 200
        mock_response.usage_metadata.total_token_count = 700

        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_cls.return_value = mock_client

            result = analyzer.analyze(
                _create_sample_image(),
                visual_matches=[VisualMatch(title="Air Jordan 1 Chicago", price="$250")],
            )

            assert result is not None
            assert result.attributes.brand == "Nike"
            assert result.attributes.estimated_msrp_usd == 180.00
            assert (
                result.confidence_score
                if hasattr(result, "confidence_score")
                else result.attributes.confidence_score == 0.98
            )
            assert len(accumulator.get_records()) == 1
            rec = accumulator.get_records()[0]
            assert rec.prompt_tokens == 500
            assert rec.output_tokens == 200


class TestStudioSynthesizer:
    def test_synthesizer_not_available_without_api_key(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        synthesizer = StudioSynthesizer(api_key=None)
        assert not synthesizer.is_available
        assert synthesizer.generate(_create_sample_image()) is None

    def test_synthesizer_successful_generation(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        accumulator = UsageAccumulator()
        synthesizer = StudioSynthesizer(api_key="test-key", accumulator=accumulator)
        assert synthesizer.is_available

        output_file = tmp_path / "studio_packshot.png"

        # Mock image data in response
        img_bytes = _create_sample_image_bytes()
        mock_part = MagicMock()
        mock_part.inline_data.data = img_bytes

        mock_candidate = MagicMock()
        mock_candidate.content.parts = [mock_part]

        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]
        mock_response.usage_metadata.prompt_token_count = 1200
        mock_response.usage_metadata.candidates_token_count = 4000
        mock_response.usage_metadata.total_token_count = 5200

        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_cls.return_value = mock_client

            asset = synthesizer.generate(
                _create_sample_image(),
                output_path=output_file,
                prompt="8K packshot",
            )

            assert asset is not None
            assert isinstance(asset, GeneratedStudioAsset)
            assert Path(asset.image_path).exists()
            assert asset.prompt_used == "8K packshot"
            assert len(accumulator.get_records()) == 1


class TestCostCalculatorIntegration:
    def test_gemini_3_8_flash_pricing(self):
        # 1M prompt tokens = $0.75, 1M output tokens = $3.75
        breakdown = calculate_cost(
            {"prompt_tokens": 100_000, "output_tokens": 10_000},
            model="gemini-3.8-flash",
        )
        assert breakdown.prompt_cost_usd == pytest.approx(0.075, rel=1e-3)
        assert breakdown.output_cost_usd == pytest.approx(0.0375, rel=1e-3)
        assert breakdown.total_cost_usd == pytest.approx(0.1125, rel=1e-3)

    def test_multi_call_accumulator_telemetry(self):
        acc = UsageAccumulator(default_model="gemini-3.8-flash")
        acc.add_call(
            {"prompt_tokens": 1000, "output_tokens": 200},
            model="gemini-3.8-flash",
            key_tag="analyzer",
        )
        acc.add_call(
            {"prompt_tokens": 2000, "output_tokens": 1000},
            model="models/nano-banana-pro-preview",
            key_tag="studio",
        )

        telemetry = acc.to_dict()
        assert telemetry["calls_count"] == 2
        assert telemetry["tokens"]["prompt"] == 3000
        assert telemetry["tokens"]["output"] == 1200
        assert telemetry["tokens"]["total"] == 4200
        assert "analyzer" in telemetry["keys_used"]
        assert "studio" in telemetry["keys_used"]
        assert telemetry["cost_usd"]["total"] > 0.0


class TestClientAIIntegration:
    @pro_only
    def test_client_search_with_ai_features(self, tmp_path, monkeypatch):
        from google_lens_scraper.client import LensScraper

        monkeypatch.setenv("GEMINI_API_KEY", "test-key")

        sample_img = tmp_path / "watch.jpg"
        sample_img.write_bytes(_create_sample_image_bytes())

        sample_analysis = VisualAnalysis(
            summary="Smart Watch",
            attributes=ProductAttributes(brand="Apple", model_or_name="Watch Ultra 2"),
        )
        sample_asset = GeneratedStudioAsset(
            image_path="/tmp/studio.png",
            prompt_used="packshot",
            aspect_ratio="1:1",
            model="models/nano-banana-pro-preview",
        )

        scraper = LensScraper()
        raw_result = LensSearchResult(
            query_url="https://lens.google.com/search?p=123",
            visual_matches=[VisualMatch(title="Apple Watch", price="$799")],
        )

        with (
            patch.object(scraper, "search_file", return_value=raw_result),
            patch(
                "google_lens_scraper.ai_analyzer.VisualAnalyzer.analyze",
                return_value=sample_analysis,
            ),
            patch(
                "google_lens_scraper.ai_studio.StudioSynthesizer.generate",
                return_value=sample_asset,
            ),
            patch("google_lens_scraper._pro.license_manager.validate") as mock_val,
        ):
            mock_val.return_value.is_valid = True
            res = scraper.search(
                sample_img,
                enrich=True,
                analyze=True,
                studio=True,
            )

            assert res.commerce is not None
            assert res.analysis is not None
            assert res.analysis.attributes.brand == "Apple"
            assert res.studio_asset is not None
            assert res.studio_asset.image_path == "/tmp/studio.png"

    @pytest.mark.asyncio
    @pro_only
    async def test_async_client_search_with_ai_features(self, tmp_path, monkeypatch):
        from google_lens_scraper.async_client import AsyncLensScraper

        monkeypatch.setenv("GEMINI_API_KEY", "test-key")

        sample_img = tmp_path / "watch.jpg"
        sample_img.write_bytes(_create_sample_image_bytes())

        sample_analysis = VisualAnalysis(
            summary="Smart Watch",
            attributes=ProductAttributes(brand="Apple", model_or_name="Watch Ultra 2"),
        )

        scraper = AsyncLensScraper()
        raw_result = LensSearchResult(
            query_url="https://lens.google.com/search?p=123",
            visual_matches=[VisualMatch(title="Apple Watch", price="$799")],
        )

        with (
            patch.object(scraper, "search_file", return_value=raw_result),
            patch(
                "google_lens_scraper.ai_analyzer.VisualAnalyzer.analyze",
                return_value=sample_analysis,
            ),
            patch("google_lens_scraper._pro.license_manager.validate") as mock_val,
        ):
            mock_val.return_value.is_valid = True
            res = await scraper.search(
                sample_img,
                enrich=True,
                analyze=True,
                studio=False,
            )

            assert res.commerce is not None
            assert res.analysis is not None
            assert res.analysis.attributes.brand == "Apple"
