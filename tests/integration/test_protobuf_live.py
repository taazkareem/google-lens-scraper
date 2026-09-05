"""Integration test for the live Chromium Protobuf API endpoint."""

import pytest

from google_lens_scraper.protobuf_engine import ProtobufEngine


@pytest.mark.asyncio
async def test_live_protobuf_endpoint(synthetic_image_bytes: bytes):
    engine = ProtobufEngine()
    result = await engine.process_image_bytes(synthetic_image_bytes)

    assert "Test Lens Image" in result["ocr_text"]
    assert len(result["detected_objects"]) > 0
    assert result["search_session_id"] is not None
    assert result["server_session_id"] is not None
    assert result["search_url"] is not None
    assert "gsessionid=" in result["search_url"]
