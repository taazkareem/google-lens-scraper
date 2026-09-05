"""Unit tests for Pydantic models."""

import json

from google_lens_scraper.models import (
    KnowledgeGraph,
    LensSearchResult,
    VisualMatch,
)


def test_visual_match_defaults():
    match = VisualMatch(
        title="Sample Item",
        link="https://example.com/item",
        thumbnail="https://encrypted-tbn0.gstatic.com/thumb",
        source="example.com",
        price="$49.99",
    )
    assert match.title == "Sample Item"
    assert match.link == "https://example.com/item"
    assert match.price == "$49.99"
    assert match.source == "example.com"


def test_lens_search_result_serialization():
    res = LensSearchResult(
        query_url="https://www.google.com/search?udm=26",
        search_session_id="session123",
        ocr_text="Hello World",
        visual_matches=[
            VisualMatch(title="Match 1", link="https://example.com/1"),
            VisualMatch(title="Match 2", link="https://example.com/2"),
        ],
        knowledge_graph=KnowledgeGraph(title="Test Entity"),
    )

    assert len(res) == 2
    assert res[0].title == "Match 1"
    assert [m.title for m in res.iter_matches()] == ["Match 1", "Match 2"]

    d = res.to_dict()
    assert d["search_session_id"] == "session123"
    assert len(d["visual_matches"]) == 2
    assert d["knowledge_graph"]["title"] == "Test Entity"

    j = res.to_json()
    parsed = json.loads(j)
    assert parsed["ocr_text"] == "Hello World"
    assert parsed["visual_matches"][0]["link"] == "https://example.com/1"
