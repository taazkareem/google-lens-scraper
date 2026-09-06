"""Session management and authentication for Google Lens Scraper."""

from __future__ import annotations

import base64
import contextlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, cast

from patchright.sync_api import sync_playwright

from .config import (
    BROWSER_LAUNCH_ARGS,
    DEFAULT_CLIENT_HINTS,
    DEFAULT_USER_AGENT,
    parse_cookie_string,
)
from .exceptions import LensRateLimitError

logger = logging.getLogger(__name__)


def _load_dotenv_if_present() -> None:
    """Optionally load environment variables from a .env file if present in the current working directory."""
    env_path = Path.cwd() / ".env"
    if not env_path.is_file():
        return
    try:
        content = env_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()
            if (val.startswith('"') and val.endswith('"')) or (
                val.startswith("'") and val.endswith("'")
            ):
                val = val[1:-1]
            if key and key not in os.environ:
                os.environ[key] = val
    except Exception as e:
        logger.debug("Could not read local .env file: %s", e)


_base_session_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
_new_session_dir = _base_session_dir / "google-lens-pro"
_legacy_session_dir = _base_session_dir / "google-lens-scraper"

DEFAULT_SESSION_DIR = (
    _new_session_dir
    if _new_session_dir.exists() or not _legacy_session_dir.exists()
    else _legacy_session_dir
)
DEFAULT_SESSION_FILE = DEFAULT_SESSION_DIR / "session.json"


class SessionManager:
    """Manages persistent browser session state (cookies, tokens) to bypass Google anti-bot."""

    def __init__(self, session_path: Path | None = None):
        self.session_path = session_path or DEFAULT_SESSION_FILE

    def ensure_dir(self) -> None:
        """Ensures the config directory exists with safe permissions."""
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(Exception):
            os.chmod(self.session_path.parent, 0o700)

    def save_session(self, storage_state: dict[str, Any]) -> Path:
        """Saves Playwright storage state (cookies + local storage) securely."""
        self.ensure_dir()
        self.session_path.write_text(json.dumps(storage_state, indent=2), encoding="utf-8")
        with contextlib.suppress(Exception):
            os.chmod(self.session_path, 0o600)
        logger.info("Session state saved to %s", self.session_path)
        return self.session_path

    def load_session(self) -> dict[str, Any] | None:
        """Loads saved session state from disk or environment variables."""
        # 0. Load local .env if present in project working directory
        _load_dotenv_if_present()

        # 1. Environment variable override (ideal for cloud / Docker / CI)
        env_json = os.environ.get("LENS_STORAGE_STATE_JSON")
        if env_json:
            try:
                raw = env_json.strip()
                if not raw.startswith("{"):
                    raw = base64.b64decode(raw).decode("utf-8")
                data = json.loads(raw)
                if isinstance(data, dict) and "cookies" in data:
                    return cast(dict[str, Any], data)
            except Exception as e:
                logger.warning("Failed to parse LENS_STORAGE_STATE_JSON: %s", e)

        env_path = os.environ.get("LENS_STORAGE_STATE_PATH")
        if env_path:
            p = Path(env_path)
            if p.exists():
                try:
                    loaded = json.loads(p.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict):
                        return cast(dict[str, Any], loaded)
                except Exception as e:
                    logger.warning("Failed to read LENS_STORAGE_STATE_PATH: %s", e)

        # 2. Local config file
        if self.session_path.exists():
            try:
                data = json.loads(self.session_path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "cookies" in data:
                    return cast(dict[str, Any], data)
            except Exception as e:
                logger.warning("Failed to load session file %s: %s", self.session_path, e)

        # 3. Direct cookie string env var fallback
        env_cookies = os.environ.get("LENS_COOKIES")
        if env_cookies:
            cookies = parse_cookie_string(env_cookies)
            if cookies:
                return {"cookies": cookies, "origins": []}

        return None

    def clear_session(self) -> bool:
        """Deletes the stored session file."""
        if self.session_path.exists():
            self.session_path.unlink()
            return True
        return False

    def is_authenticated(self) -> bool:
        """Checks if a valid Google session state exists with auth cookies."""
        state = self.load_session()
        if not state or "cookies" not in state:
            return False
        cookie_names = {c.get("name") for c in state["cookies"]}
        # Google search session identifiers
        auth_signals = {"SOCS", "SID", "HSID", "SSID", "NID", "1P_JAR", "AEC"}
        return bool(cookie_names.intersection(auth_signals))

    def interactive_login(self, timeout_seconds: int = 180, wait_for_enter: bool = True) -> Path:
        """Opens a visible browser window allowing the user to sign into Google once.

        Captures the resulting session cookies and saves them for headless reuse.
        """
        logger.info("Opening interactive browser for Google Lens authentication...")
        existing_state = self.load_session()
        launch_args = list(BROWSER_LAUNCH_ARGS) + [f"--user-agent={DEFAULT_USER_AGENT}"]

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, args=launch_args)
            context_kwargs: dict[str, Any] = {
                "viewport": {"width": 1280, "height": 800},
                "user_agent": DEFAULT_USER_AGENT,
                "extra_http_headers": DEFAULT_CLIENT_HINTS,
            }
            if existing_state:
                context_kwargs["storage_state"] = existing_state
            context = browser.new_context(**context_kwargs)
            page = context.new_page()

            start_url = (
                "https://www.google.com/search?q=google"
                if existing_state and self.is_authenticated()
                else "https://accounts.google.com/ServiceLogin?hl=en"
            )
            page.goto(start_url, wait_until="domcontentloaded")

            if wait_for_enter and sys.stdin.isatty():
                print("\n" + "=" * 60)
                print(" Google Lens Authentication & Security Clearance")
                print("=" * 60)
                print("• A browser window has opened.")
                print("• If you see a Sign-In prompt, please sign into your Google account.")
                print("• If you see a CAPTCHA challenge ('unusual traffic'), click the checkbox.")
                print("• Once Google displays search results normally, press [Enter] below.")
                print("=" * 60)
                with contextlib.suppress(EOFError, KeyboardInterrupt):
                    input("\nPress [Enter] to capture credentials and finish: ")
            else:
                # Automated polling fallback
                cleared = False
                for _ in range(timeout_seconds):
                    cookies = context.cookies(["https://www.google.com", "https://lens.google.com"])
                    names = {c["name"] for c in cookies}
                    if any(n in names for n in ("SOCS", "SID", "NID")) and "sorry" not in page.url:
                        cleared = True
                        break
                    page.wait_for_timeout(1000)

                if not cleared:
                    browser.close()
                    raise LensRateLimitError(
                        "Timed out waiting for Google clearance in interactive browser."
                    )

            # Ensure lens.google.com cross-domain tokens (e.g. OSID) are established
            try:
                page.goto("https://lens.google.com/", wait_until="domcontentloaded", timeout=10000)
                page.wait_for_timeout(1500)
            except Exception:
                pass

            # Capture complete storage state
            state = cast(dict[str, Any], context.storage_state())
            saved_path = self.save_session(state)
            browser.close()
            return saved_path
