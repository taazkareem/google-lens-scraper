"""Synchronous Google Lens Scraper client."""

import io
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import httpx
from PIL import Image

from . import _pro
from ._http import redirect_or_final_url
from ._query import classify_query
from .ai_analyzer import VisualAnalyzer
from .ai_studio import StudioSynthesizer
from .config import (
    BROWSER_LAUNCH_ARGS,
    BROWSER_VIEWPORT,
    LENS_UPLOAD_BY_URL,
    LENS_UPLOAD_URL,
    NETWORK_IDLE_TIMEOUT_MS,
    RENDER_FALLBACK_MS,
    RESULTS_RENDER_TIMEOUT_MS,
    SCROLL_DISTANCE_PX,
    SCROLL_SETTLE_MS,
    UPLOAD_POLL_INTERVAL_MS,
    LensConfig,
    build_uploadbyurl_params,
    build_uploadbyurl_url,
)
from .exceptions import (
    LensConfigurationError,
    LensImageError,
    LensNetworkError,
    LensParseError,
)
from .gemini_cost_calculator.accumulator import UsageAccumulator
from .models import KnowledgeGraph, LensSearchResult, VisualMatch
from .parser import LensParser
from .protobuf_engine import ProtobufEngine
from .relevance import process_commerce_relevance
from .settings import get_gemini_billing_tier

ProgressCallback = Callable[[str], Any]


class LensScraper:
    """Synchronous client for scraping visual matches, OCR, and entities from Google Lens."""

    def __init__(self, config: LensConfig | None = None, **kwargs: Any):
        """Initializes the LensScraper client.

        Args:
            config: Optional LensConfig instance.
            **kwargs: Shortcut keyword arguments passed to LensConfig (e.g. headless, proxy, cookies).
        """
        if config is not None and kwargs:
            raise LensConfigurationError("Cannot provide both 'config' and keyword arguments.")
        self.config = config or LensConfig(**kwargs)
        self.protobuf_engine = ProtobufEngine(
            proxy=self.config.proxy, timeout=int(self.config.timeout)
        )

    @property
    def _timeout_ms(self) -> int:
        """Configured timeout expressed in milliseconds for Playwright calls."""
        return int(self.config.timeout * 1000)

    def _http_client(self, **kwargs: Any) -> httpx.Client:
        """Builds an httpx client carrying the configured timeout, proxy, and session cookies."""
        if "cookies" not in kwargs:
            kwargs["cookies"] = self.config.get_httpx_cookies()
        return httpx.Client(timeout=self.config.timeout, proxy=self.config.proxy, **kwargs)

    @contextmanager
    def _browser_page(self) -> Iterator[Any]:
        """Yields a page on a configured browser context, tearing everything down on exit.

        Honours user_data_dir (persistent profile), cdp_url (attach to a running Chrome),
        or a fresh launch, in that order.
        """
        from patchright.sync_api import sync_playwright

        storage_state = self.config.get_storage_state()
        cookies = self.config.get_playwright_cookies(storage_state)

        ua = self.config.get_user_agent()
        launch_args = list(BROWSER_LAUNCH_ARGS) + [f"--user-agent={ua}"]
        extra_headers = self.config.get_headers()

        with sync_playwright() as p:
            browser = None
            if self.config.user_data_dir:
                p_kwargs: dict[str, Any] = {
                    "user_data_dir": str(Path(self.config.user_data_dir).resolve()),
                    "executable_path": self.config.executable_path,
                    "headless": self.config.headless,
                    "args": launch_args,
                    "user_agent": ua,
                    "extra_http_headers": extra_headers,
                }
                context = p.chromium.launch_persistent_context(**p_kwargs)
                page = context.pages[0] if context.pages else context.new_page()
            elif self.config.cdp_url:
                browser = p.chromium.connect_over_cdp(self.config.cdp_url)
                context = browser.contexts[0] if browser.contexts else browser.new_context()
                page = context.new_page()
            else:
                browser = p.chromium.launch(
                    executable_path=self.config.executable_path,
                    headless=self.config.headless,
                    args=launch_args,
                )
                context_kwargs: dict[str, Any] = {
                    "viewport": dict(BROWSER_VIEWPORT),
                    "user_agent": ua,
                    "extra_http_headers": extra_headers,
                }
                if storage_state:
                    context_kwargs["storage_state"] = storage_state
                context = browser.new_context(**context_kwargs)
                page = context.new_page()

            if cookies and not storage_state:
                context.add_cookies(cookies)  # type: ignore[arg-type]

            try:
                yield page
            finally:
                context.close()
                if browser:
                    browser.close()

    @staticmethod
    def _settle(page: Any) -> None:
        """Scrolls once to trigger lazily-rendered result cards. Best effort."""
        try:
            page.mouse.wheel(0, SCROLL_DISTANCE_PX)
            page.wait_for_timeout(SCROLL_SETTLE_MS)
        except Exception:
            pass

    @staticmethod
    def _wait_for_matches(
        page: Any, timeout_ms: int
    ) -> tuple[list[VisualMatch], KnowledgeGraph | None]:
        """Polls the live DOM until the parser finds visual matches or the timeout elapses.

        A static CSS selector wait is unreliable here: Google's obfuscated card class names
        rotate, and generic attributes like data-item-id can match unrelated page elements
        before the actual match grid has hydrated. Polling the real extraction logic ties the
        wait directly to the success condition instead of guessing at markup.
        """
        deadline = time.monotonic() + timeout_ms / 1000
        matches, kg = LensParser.parse_html(page.content())
        while not matches and time.monotonic() < deadline:
            page.wait_for_timeout(UPLOAD_POLL_INTERVAL_MS)
            matches, kg = LensParser.parse_html(page.content())
        return matches, kg

    def detect(
        self,
        query: str | Path | bytes,
        on_progress: ProgressCallback | None = None,
    ) -> LensSearchResult:
        """Fast-path only: extracts OCR text and object bounds via the Protobuf API without browser rendering."""
        if on_progress:
            on_progress("Extracting OCR text & objects via Google Lens Protobuf API...")
        image_bytes = self._resolve_to_bytes(query)
        proto_data = self.protobuf_engine.process_image_bytes_sync(image_bytes)

        return LensSearchResult(
            query_url=proto_data.get("search_url"),
            search_session_id=proto_data.get("search_session_id"),
            server_session_id=proto_data.get("server_session_id"),
            ocr_text=proto_data.get("ocr_text"),
            detected_objects=proto_data.get("detected_objects", []),
            visual_matches=[],
            knowledge_graph=None,
        )

    def search_shopping(
        self,
        query: str,
        country: str | None = None,
        currency: str | None = None,
        deep: bool = False,
        max_results: int = 40,
        on_progress: ProgressCallback | None = None,
    ) -> Any:
        """Searches Google Shopping directly for verified merchant offers and price comparisons."""
        from .engines.shopping.engine import ShoppingEngine

        engine = ShoppingEngine(config=self.config)
        return engine.search(
            query=query,
            country=country,
            currency=currency,
            deep=deep,
            max_results=max_results,
            on_progress=on_progress,
        )

    def search_image(
        self,
        query: str | Path | bytes,
        enrich: bool = True,
        analyze: bool = True,
        studio: bool = False,
        studio_output: str | Path | None = None,
        studio_prompt: str | None = None,
        country: str | None = None,
        currency: str | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> LensSearchResult:
        """Explicitly executes visual image search and shopping fusion."""
        return self.search(
            query=query,
            enrich=enrich,
            analyze=analyze,
            studio=studio,
            studio_output=studio_output,
            studio_prompt=studio_prompt,
            country=country,
            currency=currency,
            on_progress=on_progress,
        )

    def ocr(
        self,
        query: str | Path | bytes,
        on_progress: ProgressCallback | None = None,
    ) -> str | None:
        """Sub-second OCR text extraction (zero-browser, fast-path Protobuf)."""
        return self.detect(query, on_progress=on_progress).ocr_text

    def fuse(
        self,
        query: str | Path | bytes,
        country: str | None = None,
        currency: str | None = None,
        enable_shopping: bool = True,
        on_progress: ProgressCallback | None = None,
    ) -> LensSearchResult:
        """Executes the complete Unified Fusion pipeline (Lens + Shopping + AI + Enrichment)."""
        res = self.search(
            query,
            enrich=False,
            analyze=False,
            country=country,
            currency=currency,
            on_progress=on_progress,
        )
        return _pro.fuse(
            res,
            config=self.config,
            enable_shopping=enable_shopping,
            on_progress=on_progress,
        )

    def search(
        self,
        query: str | Path | bytes,
        enrich: bool = True,
        analyze: bool = True,
        studio: bool = False,
        studio_output: str | Path | None = None,
        studio_prompt: str | None = None,
        country: str | None = None,
        currency: str | None = None,
        deep: bool = False,
        fuse: bool = False,
        on_progress: ProgressCallback | None = None,
    ) -> LensSearchResult:
        """Universal query dispatcher: accepts an image URL, local path, bytes, or text/UPC.

        - If input is text/UPC: Scrapes verified merchant offers directly via Google Shopping.
        - If input is an image: Performs visual discovery and executes Unified Fusion with Google Shopping.
        """

        def _notify(msg: str) -> None:
            if on_progress:
                on_progress(msg)

        kind, value = classify_query(query)

        # Smart text query dispatch: direct Google Shopping search
        if kind == "text":
            _notify(f"Searching Google Shopping for '{value}'...")
            shop_res = self.search_shopping(
                value,
                country=country,
                currency=currency,
                deep=deep,
                on_progress=on_progress,
            )
            return LensSearchResult(
                query_url=None,
                shopping=shop_res,
                visual_matches=[],
            )

        _notify("Navigating Google Lens & extracting visual matches...")
        if kind == "bytes":
            res = self.search_bytes(value)
        elif kind == "google_url":
            res = self.search_url(value)
        elif kind == "image_url":
            res = self.search_image_url(value)
        else:
            res = self.search_file(value)

        accumulator = UsageAccumulator(
            default_model="gemini-3.8-flash",
            billing_tier=get_gemini_billing_tier(),
        )

        if analyze:
            _notify("Running Gemini 3.8 Flash multimodal analysis...")
            analyzer = VisualAnalyzer(accumulator=accumulator)
            res.analysis = analyzer.analyze(
                image_input=query,
                visual_matches=res.visual_matches,
                knowledge_graph=res.knowledge_graph,
                ocr_text=res.ocr_text,
            )

        if fuse:
            _notify("Fusing Google Lens matches & Google Shopping offers...")
            res = _pro.fuse(res, config=self.config, on_progress=on_progress)
        elif enrich:
            match_count = len(res.visual_matches)
            _notify(f"Enriching merchant pricing & canonical URLs ({match_count} matches)...")
            res = _pro.enrich(res, on_progress=on_progress)

        if res.commerce:
            res.commerce = process_commerce_relevance(
                res.commerce,
                res.analysis,
                visual_matches=res.visual_matches,
                knowledge_graph=res.knowledge_graph,
                ocr_text=res.ocr_text,
            )
            res.analysis = res.analysis or res.commerce.analysis

        if studio:
            _notify("Synthesizing 8K commercial product packshot...")
            synthesizer = StudioSynthesizer(accumulator=accumulator)
            if synthesizer.is_available:
                res.studio_asset = synthesizer.generate(
                    image_input=query,
                    output_path=studio_output,
                    prompt=studio_prompt,
                )

        if accumulator.get_records():
            res.cost = accumulator.to_dict()
            if res.commerce:
                res.commerce.cost = res.cost

        return res


    def upload_image(self, image_bytes: bytes) -> str:
        """Uploads image bytes to Google Lens ingestion and returns the generated search URL."""
        try:
            with Image.open(io.BytesIO(image_bytes)) as im:
                w, h = im.size
        except Exception as e:
            raise LensImageError(f"Invalid image format: {e}") from e

        files: dict[str, Any] = {
            "encoded_image": ("image.jpg", image_bytes, "image/jpeg"),
            "processed_image_dimensions": (None, f"{w},{h}"),
        }
        params = {
            "hl": self.config.language,
            "re": "df",
            "ep": "cntpubb",
        }

        try:
            with self._http_client(
                headers=self.config.get_headers(), follow_redirects=False
            ) as client:
                resp = client.post(
                    LENS_UPLOAD_URL,
                    params=params,
                    files=files,  # type: ignore[arg-type]
                )
                return redirect_or_final_url(resp)
        except Exception as e:
            raise LensNetworkError(f"Failed to upload image to Google Lens: {e}") from e

    def upload_image_url(self, image_url: str) -> str:
        """Resolves an image URL into a Google Lens search result URL."""
        params = build_uploadbyurl_params(image_url, self.config.language)
        try:
            with self._http_client(
                headers=self.config.get_headers(), follow_redirects=False
            ) as client:
                resp = client.get(LENS_UPLOAD_BY_URL, params=params)
                return redirect_or_final_url(resp)
        except Exception as e:
            raise LensNetworkError(f"Failed to resolve image URL on Lens: {e}") from e

    def search_bytes(self, image_bytes: bytes) -> LensSearchResult:
        """Searches using raw image bytes."""
        # 1. Fast Protobuf OCR and Object Detection
        proto_data = self.protobuf_engine.process_image_bytes_sync(image_bytes)

        # 2. Authentic in-browser visual search
        web_res = self._search_image_in_browser(image_bytes)

        return LensSearchResult(
            query_url=web_res.query_url,
            search_session_id=proto_data.get("search_session_id") or web_res.search_session_id,
            server_session_id=proto_data.get("server_session_id") or web_res.server_session_id,
            ocr_text=proto_data.get("ocr_text"),
            detected_objects=proto_data.get("detected_objects", []),
            visual_matches=web_res.visual_matches,
            knowledge_graph=web_res.knowledge_graph,
        )

    def _search_image_in_browser(self, image_bytes: bytes) -> LensSearchResult:
        """Performs in-browser visual search using Playwright/Patchright with direct file input."""
        with self._browser_page() as page:
            page.goto(
                "https://www.google.com",
                wait_until="domcontentloaded",
                timeout=self._timeout_ms,
            )
            LensParser.check_url(page.url)

            # Click the "Search by image" camera button to reveal the file input
            camera_btn = page.wait_for_selector(
                'div[role="button"][aria-label*="Search by image"], div[aria-label*="Search by image"]',
                timeout=self._timeout_ms,
            )
            if camera_btn:
                camera_btn.click()

            file_input = page.wait_for_selector(
                'input[type="file"]',
                state="attached",
                timeout=self._timeout_ms,
            )
            if not file_input:
                raise LensParseError("Could not find Google Lens file upload input.")

            file_input.set_input_files(
                {"name": "image.jpg", "mimeType": "image/jpeg", "buffer": image_bytes}
            )

            # Wait for Google to process upload and transition to search results URL
            for _ in range(max(10, int(self.config.timeout))):
                page.wait_for_timeout(UPLOAD_POLL_INTERVAL_MS)
                if "vsrid=" in page.url:
                    break

            current_url = page.url
            LensParser.check_url(current_url)

            self._settle(page)

            visual_matches, kg = self._wait_for_matches(page, RESULTS_RENDER_TIMEOUT_MS)

            return LensSearchResult(
                query_url=current_url,
                visual_matches=visual_matches,
                knowledge_graph=kg,
            )

    def search_file(self, file_path: str | Path) -> LensSearchResult:
        """Searches using a local image file."""
        path = Path(file_path)
        if not path.exists():
            raise LensImageError(f"File not found: {path}")
        return self.search_bytes(path.read_bytes())

    def search_image_url(self, image_url: str) -> LensSearchResult:
        """Searches using a public image URL."""
        image_bytes = self._fetch_image_bytes(image_url)

        # 1. Protobuf detection
        proto_data = self.protobuf_engine.process_image_bytes_sync(image_bytes)

        # 2. In-browser visual search via authenticated uploadbyurl navigation
        upload_url = build_uploadbyurl_url(image_url, self.config.language)
        web_res = self.search_url(upload_url)

        return LensSearchResult(
            query_url=web_res.query_url or upload_url,
            search_session_id=proto_data.get("search_session_id"),
            server_session_id=proto_data.get("server_session_id"),
            ocr_text=proto_data.get("ocr_text"),
            detected_objects=proto_data.get("detected_objects", []),
            visual_matches=web_res.visual_matches,
            knowledge_graph=web_res.knowledge_graph,
        )

    def search_url(self, url: str) -> LensSearchResult:
        """Fetches and parses a Google Lens search URL using Patchright / Playwright."""
        with self._browser_page() as page:
            page.goto(url, wait_until="domcontentloaded", timeout=self._timeout_ms)

            try:
                page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_TIMEOUT_MS)
            except Exception:
                page.wait_for_timeout(RENDER_FALLBACK_MS)

            LensParser.check_url(page.url)

            self._settle(page)

            current_url = page.url
            LensParser.check_url(current_url)

            visual_matches, kg = self._wait_for_matches(page, RESULTS_RENDER_TIMEOUT_MS)

            return LensSearchResult(
                query_url=current_url,
                visual_matches=visual_matches,
                knowledge_graph=kg,
            )

    def _fetch_image_bytes(self, image_url: str) -> bytes:
        """Downloads raw image bytes from a public URL."""
        try:
            with self._http_client() as client:
                resp = client.get(
                    image_url, headers=self.config.get_headers(), follow_redirects=True
                )
                resp.raise_for_status()
                return resp.content
        except Exception as e:
            raise LensImageError(f"Failed to fetch image from URL '{image_url}': {e}") from e

    def _resolve_to_bytes(self, query: str | Path | bytes) -> bytes:
        """Helper to convert any input into image bytes."""
        if isinstance(query, bytes):
            return query
        path = Path(str(query))
        if path.exists() and path.is_file():
            return path.read_bytes()
        query_str = str(query).strip()
        if query_str.startswith(("http://", "https://")):
            return self._fetch_image_bytes(query_str)
        raise LensConfigurationError(f"Cannot resolve '{query}' to image bytes.")


# Canonical alias for the unified client
GoogleLens = LensScraper

__all__ = ["GoogleLens", "LensScraper", "ProgressCallback"]

