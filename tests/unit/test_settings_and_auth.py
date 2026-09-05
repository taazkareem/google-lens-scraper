"""Unit tests for settings management."""

from __future__ import annotations

from google_lens_scraper.settings import (
    get_gemini_api_key,
    load_config,
    save_config,
    set_gemini_api_key,
)


def test_settings_save_and_load(tmp_path, monkeypatch):
    test_config_dir = tmp_path / ".config" / "google-lens-scraper"
    test_config_file = test_config_dir / "config.json"
    monkeypatch.setattr("google_lens_scraper.settings.CONFIG_DIR", test_config_dir)
    monkeypatch.setattr("google_lens_scraper.settings.CONFIG_FILE", test_config_file)

    assert load_config() == {}

    save_config({"foo": "bar", "count": 42})
    loaded = load_config()
    assert loaded == {"foo": "bar", "count": 42}


def test_settings_gemini_key_resolution(tmp_path, monkeypatch):
    test_config_dir = tmp_path / ".config" / "google-lens-scraper"
    test_config_file = test_config_dir / "config.json"
    monkeypatch.setattr("google_lens_scraper.settings.CONFIG_DIR", test_config_dir)
    monkeypatch.setattr("google_lens_scraper.settings.CONFIG_FILE", test_config_file)

    # Empty
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert get_gemini_api_key() is None

    # From config
    set_gemini_api_key("cfg-gemini-key-123")
    assert get_gemini_api_key() == "cfg-gemini-key-123"

    # Env var takes precedence
    monkeypatch.setenv("GEMINI_API_KEY", "env-gemini-key-999")
    assert get_gemini_api_key() == "env-gemini-key-999"
