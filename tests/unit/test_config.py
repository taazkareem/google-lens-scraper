"""Unit tests for LensConfig."""

from google_lens_scraper.config import LensConfig


def test_lens_config_defaults():
    cfg = LensConfig()
    assert cfg.headless is True
    assert cfg.timeout == 30.0
    cookies = cfg.get_playwright_cookies()
    assert len(cookies) >= 2
    assert any(c["name"] == "SOCS" for c in cookies)


def test_lens_config_custom_cookies():
    cfg = LensConfig(cookies="SID=abc123xyz; HSID=def456uvw")
    cookies = cfg.get_playwright_cookies()
    names = [c["name"] for c in cookies]
    assert "SID" in names
    assert "HSID" in names
    sid_cookie = next(c for c in cookies if c["name"] == "SID")
    assert sid_cookie["value"] == "abc123xyz"


def test_lens_config_dict_cookies():
    cfg = LensConfig(cookies={"MY_COOKIE": "my_val"})
    cookies = cfg.get_playwright_cookies()
    assert any(c["name"] == "MY_COOKIE" and c["value"] == "my_val" for c in cookies)
