"""SPDX-FileCopyrightText: © 2026 Talib Kareem <taazkareem@icloud.com>
SPDX-License-Identifier: MIT

Configuration, settings, and persistent configuration management.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlencode

from ..gemini_cost_calculator import BILLING_TIERS, BillingTier

if TYPE_CHECKING:
    from .auth import SessionManager

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

CHROME_MACOS_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

LENS_UPLOAD_URL = "https://lens.google.com/v3/upload"
LENS_UPLOAD_BY_URL = "https://lens.google.com/uploadbyurl"
GOOGLE_IMAGE_UPLOAD_URL = "https://www.google.com/?olud"
GOOGLE_SHOPPING_SEARCH_URL = "https://www.google.com/search"

BROWSER_LAUNCH_ARGS = (
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-infobars",
)
BROWSER_VIEWPORT = {"width": 1440, "height": 1000}

DEFAULT_CLIENT_HINTS: dict[str, str] = {
    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
}

RESULTS_RENDER_TIMEOUT_MS = 15_000
NETWORK_IDLE_TIMEOUT_MS = 8_000
RENDER_FALLBACK_MS = 3_000
UPLOAD_POLL_INTERVAL_MS = 1_000
SCROLL_SETTLE_MS = 1_000
SCROLL_DISTANCE_PX = 1_500

GOOGLE_COOKIE_DOMAIN = ".google.com"

_DEFAULT_CONSENT_COOKIES: tuple[dict[str, Any], ...] = (
    {
        "name": "SOCS",
        "value": "CAESHAgBEhJnd3NfMjAyMzA4MTAtMF9SQzIaAmVuIAEaBgiAo_CmBg",
        "domain": GOOGLE_COOKIE_DOMAIN,
        "path": "/",
    },
    {"name": "CONSENT", "value": "PENDING+999", "domain": GOOGLE_COOKIE_DOMAIN, "path": "/"},
)

_base_config_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
_new_config_dir = _base_config_dir / "google-lens-pro"
_legacy_config_dir = _base_config_dir / "google-lens-scraper"

CONFIG_DIR = (
    _new_config_dir
    if _new_config_dir.exists() or not _legacy_config_dir.exists()
    else _legacy_config_dir
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
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()
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


def get_gemini_billing_tier() -> BillingTier:
    """Resolves Gemini billing tier ('unknown', 'free', or 'paid'). Defaults to 'unknown'."""
    env_tier = os.environ.get("GEMINI_BILLING_TIER")
    if env_tier and env_tier.strip().lower() in BILLING_TIERS:
        return cast(BillingTier, env_tier.strip().lower())
    tier = load_config().get("gemini_billing_tier")
    if isinstance(tier, str) and tier.strip().lower() in BILLING_TIERS:
        return cast(BillingTier, tier.strip().lower())
    return "unknown"


def set_gemini_billing_tier(tier: str) -> None:
    """Persists a Gemini billing tier into local config.json."""
    config = load_config()
    config["gemini_billing_tier"] = tier.strip().lower()
    save_config(config)


def build_uploadbyurl_params(image_url: str, language: str) -> dict[str, str]:
    """Builds the query params for a lens.google.com/uploadbyurl request."""
    return {"url": image_url, "hl": language, "re": "df", "ep": "cntpubb"}


def build_uploadbyurl_url(image_url: str, language: str) -> str:
    """Builds the full lens.google.com/uploadbyurl request URL for direct browser navigation."""
    return f"{LENS_UPLOAD_BY_URL}?{urlencode(build_uploadbyurl_params(image_url, language))}"


def parse_cookie_string(raw: str) -> list[dict[str, Any]]:
    """Parses a 'name=value; name2=value2' cookie header into Playwright cookie objects."""
    cookies: list[dict[str, Any]] = []
    for pair in raw.split(";"):
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        name, value = pair.split("=", 1)
        cookies.append(
            {
                "name": name.strip(),
                "value": value.strip(),
                "domain": GOOGLE_COOKIE_DOMAIN,
                "path": "/",
            }
        )
    return cookies


@dataclass
class LensConfig:
    """Settings and anti-bot configuration for Google Lens & Google Shopping operations."""

    headless: bool = True
    timeout: float = 30.0
    proxy: str | None = None
    user_data_dir: str | None = None
    cookies: dict[str, str] | str | list[dict[str, Any]] | None = None
    cdp_url: str | None = None
    use_saved_session: bool = True
    session_path: str | Path | None = None
    real_chrome: bool = False
    executable_path: str | None = None
    language: str = "en"
    region: str = "US"
    country: str = "US"
    currency: str = "USD"
    user_agent: str | None = None
    extra_headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.session_path is not None:
            self.session_path = Path(self.session_path).expanduser()

        # Synchronize region and country
        if self.country and self.country != "US" and self.region == "US":
            self.region = self.country
        elif self.region and self.region != "US" and self.country == "US":
            self.country = self.region

        if self.real_chrome and self.executable_path is None and os.path.exists(CHROME_MACOS_PATH):
            self.executable_path = CHROME_MACOS_PATH

    def get_user_agent(self) -> str:
        """Returns the configured User-Agent, falling back to the package default."""
        return self.user_agent or DEFAULT_USER_AGENT

    def get_headers(self, **extra: str) -> dict[str, str]:
        """Builds request headers with User-Agent, Chrome Client Hints, and extras."""
        return {
            "User-Agent": self.get_user_agent(),
            **DEFAULT_CLIENT_HINTS,
            **self.extra_headers,
            **extra,
        }

    def get_session_manager(self) -> SessionManager:
        """Returns a SessionManager bound to this configuration's session path."""
        from .auth import SessionManager

        return SessionManager(cast("Path | None", self.session_path))

    def get_storage_state(self) -> dict[str, Any] | None:
        """Retrieves storage state (cookies + origins) if available."""
        if not self.use_saved_session:
            return None
        return self.get_session_manager().load_session()

    def get_playwright_cookies(
        self, storage_state: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Converts configured cookies into Playwright cookie objects."""
        cookie_list: list[dict[str, Any]] = [dict(c) for c in _DEFAULT_CONSENT_COOKIES]

        if not self.cookies and self.use_saved_session:
            state = storage_state if storage_state is not None else self.get_storage_state()
            if state and state.get("cookies"):
                names = {c["name"] for c in state["cookies"]}
                merged = list(state["cookies"])
                merged.extend(c for c in cookie_list if c["name"] not in names)
                return cast(list[dict[str, Any]], merged)

        if not self.cookies:
            return cookie_list

        if isinstance(self.cookies, str):
            cookie_list.extend(parse_cookie_string(self.cookies))
        elif isinstance(self.cookies, dict):
            cookie_list.extend(
                {
                    "name": str(key).strip(),
                    "value": str(val).strip(),
                    "domain": GOOGLE_COOKIE_DOMAIN,
                    "path": "/",
                }
                for key, val in self.cookies.items()
            )
        elif isinstance(self.cookies, list):
            cookie_list.extend(
                {
                    "name": str(c["name"]),
                    "value": str(c["value"]),
                    "domain": c.get("domain", GOOGLE_COOKIE_DOMAIN),
                    "path": c.get("path", "/"),
                }
                for c in self.cookies
                if isinstance(c, dict) and "name" in c and "value" in c
            )

        return cookie_list

    def get_httpx_cookies(self) -> dict[str, str]:
        """Converts configured cookies into a name-value mapping for httpx requests."""
        return {
            str(c["name"]): str(c["value"])
            for c in self.get_playwright_cookies()
            if "name" in c and "value" in c
        }
