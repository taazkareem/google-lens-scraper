"""Unit tests for LensParser."""

import pytest

from google_lens_scraper.exceptions import LensRateLimitError
from google_lens_scraper.parser import LensParser


def test_parse_sample_html(sample_lens_html: str):
    matches, kg = LensParser.parse_html(sample_lens_html)
    assert len(matches) == 2

    m1 = matches[0]
    assert m1.link == "https://example.com/products/sneaker"
    assert "Nike Air Jordan" in m1.title
    assert "encrypted-tbn0" in m1.thumbnail
    assert m1.price == "$180.00"

    m2 = matches[1]
    assert m2.link == "https://store.example.com/shoes/vintage-runner"
    assert "Vintage Runner" in m2.title

    assert kg is not None
    assert kg.title == "Air Jordan 1"


def test_rate_limit_detection(sample_rate_limited_html: str):
    with pytest.raises(LensRateLimitError):
        LensParser.parse_html(sample_rate_limited_html)

    with pytest.raises(LensRateLimitError):
        LensParser.check_url("https://www.google.com/sorry/index?continue=xyz")
