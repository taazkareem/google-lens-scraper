"""SPDX-FileCopyrightText: © 2026 Talib Kareem <taazkareem@icloud.com>
SPDX-License-Identifier: MIT

Smart query classification for visual search vs text/shopping search.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

QueryKind = Literal["bytes", "google_url", "image_url", "file", "text"]


IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".bmp",
    ".tiff",
    ".tif",
    ".svg",
    ".avif",
    ".heic",
    ".ico",
}


def classify_query(query: str | Path | bytes) -> tuple[QueryKind, Any]:
    """Determines which search entrypoint a raw query belongs to.

    Returns:
        - "bytes": Raw image byte sequence
        - "google_url": Google Lens or Google Shopping result URL
        - "image_url": Remote HTTP/HTTPS image URL
        - "file": Existing local image file path or image filename
        - "text": Product title, SKU, or search keyword
    """
    if isinstance(query, bytes):
        return "bytes", query

    query_str = str(query).strip()
    parsed = urlparse(query_str)

    if parsed.scheme in ("http", "https"):
        if "google.com" in parsed.netloc:
            return "google_url", query_str
        return "image_url", query_str

    path = Path(query_str).expanduser()
    if (path.exists() and path.is_file()) or path.suffix.lower() in IMAGE_EXTENSIONS:
        return "file", path

    # If it's not a file or URL, it's a product title, barcode, or text query
    return "text", query_str
