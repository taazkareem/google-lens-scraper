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
    assert m1.thumbnail is not None
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


def test_extract_from_dom_cards_with_container_prices():
    html = """
    <div class="main-container">
        <div class="N54PNb card-wrapper">
            <a href="https://example.com/shoe-1">
                <div>Nike Store</div>
                <div>Nike Air Max 270</div>
            </a>
            <div class="price-container">
                <span class="price-badge">$150.00</span>
            </div>
        </div>
        <div class="card-item">
            <a href="https://example.com/shoe-2">
                <div>SneakerWorld</div>
                <div>Vintage Runner</div>
            </a>
            <div>
                <span>95 €</span>
            </div>
        </div>
        <div class="card-item">
            <a href="https://example.com/shoe-3">
                <div>Luxe</div>
                <div>Luxury Sneaker</div>
            </a>
            <div>
                <span>£1,250.00</span>
            </div>
        </div>
    </div>
    """
    matches = LensParser.extract_from_dom_cards(html)
    assert len(matches) == 3

    assert matches[0].title == "Nike Air Max 270"
    assert matches[0].source == "Nike Store"
    assert matches[0].price == "$150.00"

    assert matches[1].title == "Vintage Runner"
    assert matches[1].source == "SneakerWorld"
    assert matches[1].price == "95 €"

    assert matches[2].title == "Luxury Sneaker"
    assert matches[2].source == "Luxe"
    assert matches[2].price == "£1,250.00"
