"""Unit-test fixtures."""

import contextlib

import pytest


def _blocked_browser(*_args, **_kwargs):
    raise RuntimeError("store-resolver browser disabled in unit tests")


@pytest.fixture(autouse=True)
def _no_real_store_browser(monkeypatch):
    """Keep DirectStoreResolver from launching a real browser during unit tests.

    Full-pipeline tests reach ``resolve_async`` with live URLs; without this they
    would spin up Chromium. ``test_store_resolver`` patches ``_make_stealth_session``
    with a fake session, overriding this. On the MIT source tree the Pro resolver
    is absent, so the patch target simply isn't there.
    """
    with contextlib.suppress(ImportError, AttributeError):
        monkeypatch.setattr(
            "google_lens_pro.commerce.resolver._make_stealth_session",
            _blocked_browser,
            raising=True,
        )
