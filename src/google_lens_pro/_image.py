"""Shared image loading for the AI analysis and studio engines."""

from __future__ import annotations

import io
import logging
from pathlib import Path

import httpx
from PIL import Image

logger = logging.getLogger(__name__)

MAX_IMAGE_DIMENSION = 1600


def load_image(image_input: str | Path | bytes | Image.Image) -> Image.Image | None:
    """Loads an image from a PIL image, http(s) URL, local path, or raw bytes.

    Anything larger than ``MAX_IMAGE_DIMENSION`` on its longest edge is downscaled in place.
    Returns ``None`` when the input cannot be resolved to an image.
    """
    img: Image.Image | None = None

    if isinstance(image_input, Image.Image):
        img = image_input
    elif isinstance(image_input, bytes):
        img = Image.open(io.BytesIO(image_input))
    elif isinstance(image_input, str) and image_input.startswith(("http://", "https://")):
        try:
            resp = httpx.get(
                image_input,
                timeout=15.0,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content))
        except Exception as exc:
            logger.warning(f"Could not load image from URL {image_input!r}: {exc}")
            return None
    elif isinstance(image_input, (str, Path)):
        path = Path(image_input)
        if path.is_file():
            img = Image.open(path)

    if img is not None and max(img.size) > MAX_IMAGE_DIMENSION:
        img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))
    return img
