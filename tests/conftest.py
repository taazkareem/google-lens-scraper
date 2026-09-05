"""Pytest fixtures for Google Lens Scraper tests."""

import io

import pytest
from PIL import Image, ImageDraw


@pytest.fixture
def sample_lens_html() -> str:
    """Provides a realistic sample Google Lens HTML containing an AF_initDataCallback payload."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Google Lens</title></head>
    <body>
    <div id="main">
        <h1>Google Lens Results</h1>
    </div>
    <script nonce="test1234">
    AF_initDataCallback({
        key: 'ds:1',
        hash: '1',
        data: [
            "dummy_header",
            [
                [
                    "https://example.com/products/sneaker",
                    "Nike Air Jordan 1 High OG",
                    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcExample1",
                    "Nike Official",
                    "$180.00"
                ],
                [
                    "https://store.example.com/shoes/vintage-runner",
                    "Vintage Runner Sneakers Classic",
                    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcExample2",
                    "SneakerStore",
                    "$120.00"
                ]
            ]
        ],
        sideChannel: {}
    });
    </script>
    <div data-entityname="Air Jordan 1"></div>
    </body>
    </html>
    """


@pytest.fixture
def sample_rate_limited_html() -> str:
    """Sample Google sorry/index challenge HTML."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>https://www.google.com/sorry/index?continue=...</title></head>
    <body>
        <h1>About this page</h1>
        <p>Our systems have detected unusual traffic from your computer network.</p>
    </body>
    </html>
    """


@pytest.fixture
def synthetic_image_bytes() -> bytes:
    """Generates synthetic JPEG image bytes for image processing tests."""
    img = Image.new("RGB", (200, 100), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    draw.text((10, 40), "Test Lens Image", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()
