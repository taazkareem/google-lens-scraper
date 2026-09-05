"""Configuration and settings dataclass for Google Lens Scraper."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlencode

if TYPE_CHECKING:
    from .session import SessionManager

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

CHROME_MACOS_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

LENS_UPLOAD_URL = "https://lens.google.com/v3/upload"
LENS_UPLOAD_BY_URL = "https://lens.google.com/uploadbyurl"
GOOGLE_IMAGE_UPLOAD_URL = "https://www.google.com/?olud"

# Chromium flags used for every Lens browser session.
BROWSER_LAUNCH_ARGS = (
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-infobars",
)
BROWSER_VIEWPORT = {"width": 1440, "height": 1000}

# Standard Chrome client hints to prevent headless detection via sec-ch-ua headers.
DEFAULT_CLIENT_HINTS: dict[str, str] = {
    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
}

# Browser interaction timings, in milliseconds.
RESULTS_RENDER_TIMEOUT_MS = 15_000
NETWORK_IDLE_TIMEOUT_MS = 8_000
RENDER_FALLBACK_MS = 3_000
UPLOAD_POLL_INTERVAL_MS = 1_000
SCROLL_SETTLE_MS = 1_000
SCROLL_DISTANCE_PX = 1_500

GOOGLE_COOKIE_DOMAIN = ".google.com"

# Consent cookies that keep Google from serving the EU consent wall.
_DEFAULT_CONSENT_COOKIES: tuple[dict[str, Any], ...] = (
    {
        "name": "SOCS",
        "value": "CAESHAgBEhJnd3NfMjAyMzA4MTAtMF9SQzIaAmVuIAEaBgiAo_CmBg",
        "domain": GOOGLE_COOKIE_DOMAIN,
        "path": "/",
    },
    {"name": "CONSENT", "value": "PENDING+999", "domain": GOOGLE_COOKIE_DOMAIN, "path": "/"},
)


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
    """Settings and anti-bot configuration for Google Lens operations."""

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
    user_agent: str | None = None
    extra_headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Normalize here so SessionManager always receives the Path it expects.
        if self.session_path is not None:
            self.session_path = Path(self.session_path).expanduser()

        # Auto-detect real Chrome on macOS if available and requested
        if self.real_chrome and self.executable_path is None and os.path.exists(CHROME_MACOS_PATH):
            self.executable_path = CHROME_MACOS_PATH

    def get_user_agent(self) -> str:
        """Returns the configured User-Agent, falling back to the package default."""
        return self.user_agent or DEFAULT_USER_AGENT

    def get_headers(self, **extra: str) -> dict[str, str]:
        """Builds request headers from the User-Agent, Chrome Client Hints, configured extras, and per-call additions."""
        return {
            "User-Agent": self.get_user_agent(),
            **DEFAULT_CLIENT_HINTS,
            **self.extra_headers,
            **extra,
        }

    def get_session_manager(self) -> SessionManager:
        """Returns a SessionManager bound to this configuration's session path."""
        from .session import SessionManager

        return SessionManager(cast("Path | None", self.session_path))

    def get_storage_state(self) -> dict[str, Any] | None:
        """Retrieves storage state (cookies + origins) if available."""
        if not self.use_saved_session:
            return None
        return self.get_session_manager().load_session()

    def get_playwright_cookies(
        self, storage_state: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Converts configured cookies into Playwright cookie objects.

        Args:
            storage_state: Already-loaded session state, so callers that need both this
                and the storage state don't re-read the session file from disk.
        """
        cookie_list: list[dict[str, Any]] = [dict(c) for c in _DEFAULT_CONSENT_COOKIES]

        # 1. Check saved session state first if enabled
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
