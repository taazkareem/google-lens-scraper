"""Shared query classification for the sync and async clients."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from .exceptions import LensConfigurationError

QueryKind = Literal["bytes", "google_url", "image_url", "file"]


def classify_query(query: str | Path | bytes) -> tuple[QueryKind, Any]:
    """Determines which search entrypoint a raw query belongs to.

    Returns the query kind along with the normalized value to hand to the
    matching client method. Raises LensConfigurationError if the query matches none.
    """
    if isinstance(query, bytes):
        return "bytes", query

    query_str = str(query).strip()
    parsed = urlparse(query_str)

    if parsed.scheme in ("http", "https"):
        if "google.com" in parsed.netloc:
            return "google_url", query_str
        return "image_url", query_str

    path = Path(query_str)
    if path.exists() and path.is_file():
        return "file", path

    raise LensConfigurationError(
        f"Unable to determine query type for '{query_str}'. "
        "Pass an image URL, Google search URL, or valid local file path."
    )
