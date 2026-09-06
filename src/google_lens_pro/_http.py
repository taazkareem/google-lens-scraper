"""Shared HTTP helpers for the sync and async clients."""

import httpx


def redirect_or_final_url(resp: httpx.Response) -> str:
    """Returns the Location that Lens redirected to, else the response's own URL."""
    if resp.status_code in (302, 303, 307):
        location = resp.headers.get("Location")
        if location:
            return str(location)

    resp.raise_for_status()
    return str(resp.url)
