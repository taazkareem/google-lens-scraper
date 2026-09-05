"""Persistent user configuration management for Google Lens Scraper."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_DIR = (
    Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "google-lens-scraper"
)
CONFIG_FILE = CONFIG_DIR / "config.json"


def ensure_config_dir() -> Path:
    """Ensures configuration directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def load_config() -> dict[str, Any]:
    """Loads user configuration dictionary from config.json."""
    if not CONFIG_FILE.exists():
        return {}
    try:
        loaded = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            return loaded
        return {}
    except Exception as e:
        logger.debug(f"Failed to read config.json: {e}")
        return {}


def save_config(data: dict[str, Any]) -> None:
    """Saves user configuration dictionary to config.json."""
    ensure_config_dir()
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_gemini_api_key() -> str | None:
    """Resolves Gemini API key from environment variable or local config."""
    # 1. Environment variable has highest precedence
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    # 2. Local config file
    config = load_config()
    key = config.get("gemini_api_key")
    if key and isinstance(key, str) and key.strip():
        return key.strip()

    return None


def set_gemini_api_key(key: str) -> None:
    """Persists a Gemini API key into local config.json."""
    config = load_config()
    config["gemini_api_key"] = key.strip()
    save_config(config)
