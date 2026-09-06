"""Asynchronous Google Lens Scraper client."""

import asyncio
import io
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
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


class AsyncLensScraper:
    """Asynchronous client for scraping visual matches, OCR, and entities from Google Lens."""

    def __init__(self, config: LensConfig | None = None, **kwargs: Any):
        """Initializes the AsyncLensScraper client."""
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

    def _http_client(self, **kwargs: Any) -> httpx.AsyncClient:
        """Builds an httpx client carrying the configured timeout, proxy, and session cookies."""
        if "cookies" not in kwargs:
            kwargs["cookies"] = self.config.get_httpx_cookies()
        return httpx.AsyncClient(timeout=self.config.timeout, proxy=self.config.proxy, **kwargs)

    @asynccontextmanager
    async def _browser_page(self) -> AsyncIterator[Any]:
        """Yields a page on a configured browser context, tearing everything down on exit.

        Honours user_data_dir (persistent profile), cdp_url (attach to a running Chrome),
        or a fresh launch, in that order.
        """
        from patchright.async_api import async_playwright

        storage_state = self.config.get_storage_state()
        cookies = self.config.get_playwright_cookies(storage_state)

        ua = self.config.get_user_agent()
        launch_args = list(BROWSER_LAUNCH_ARGS) + [f"--user-agent={ua}"]
        extra_headers = self.config.get_headers()

        async with async_playwright() as p:
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
                context = await p.chromium.launch_persistent_context(**p_kwargs)
                page = context.pages[0] if context.pages else await context.new_page()
            elif self.config.cdp_url:
                browser = await p.chromium.connect_over_cdp(self.config.cdp_url)
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                page = await context.new_page()
            else:
                browser = await p.chromium.launch(
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
                context = await browser.new_context(**context_kwargs)
                page = await context.new_page()

            if cookies and not storage_state:
                await context.add_cookies(cookies)  # type: ignore[arg-type]

            try:
                yield page
            finally:
                await context.close()
                if browser:
                    await browser.close()

    @staticmethod
    async def _settle(page: Any) -> None:
        """Scrolls once to trigger lazily-rendered result cards. Best effort."""
        try:
            await page.mouse.wheel(0, SCROLL_DISTANCE_PX)
            await page.wait_for_timeout(SCROLL_SETTLE_MS)
        except Exception:
            pass

    @staticmethod
    async def _wait_for_matches(
        page: Any, timeout_ms: int
    ) -> tuple[list[VisualMatch], KnowledgeGraph | None]:
        """Polls the live DOM until the parser finds visual matches or the timeout elapses.

        A static CSS selector wait is unreliable here: Google's obfuscated card class names
        rotate, and generic attributes like data-item-id can match unrelated page elements
        before the actual match grid has hydrated. Polling the real extraction logic ties the
        wait directly to the success condition instead of guessing at markup.
        """
        deadline = time.monotonic() + timeout_ms / 1000
        matches, kg = LensParser.parse_html(await page.content())
        while not matches and time.monotonic() < deadline:
            await page.wait_for_timeout(UPLOAD_POLL_INTERVAL_MS)
            matches, kg = LensParser.parse_html(await page.content())
        return matches, kg

    async def detect(self, query: str | Path | bytes) -> LensSearchResult:
        """Fast-path only (async): extracts OCR and objects via Protobuf without browser rendering."""
        image_bytes = await self._resolve_to_bytes(query)
        proto_data = await self.protobuf_engine.process_image_bytes(image_bytes)

        return LensSearchResult(
            query_url=proto_data.get("search_url"),
            search_session_id=proto_data.get("search_session_id"),
            server_session_id=proto_data.get("server_session_id"),
            ocr_text=proto_data.get("ocr_text"),
            detected_objects=proto_data.get("detected_objects", []),
            visual_matches=[],
            knowledge_graph=None,
        )

    async def search(
        self,
        query: str | Path | bytes,
        enrich: bool = True,
        analyze: bool = True,
        studio: bool = False,
        studio_output: str | Path | None = None,
        studio_prompt: str | None = None,
    ) -> LensSearchResult:
        """Universal query dispatcher (async).

        Args:
            query: Public image URL, local image path, bytes, or Google Lens result URL.
            enrich: If True, enriches visual matches with e-commerce pricing, clean canonical URLs,
                   and merchant classification (requires Polar.sh license for full data; otherwise
                   returns a 1-item teaser preview). Defaults to True.
            analyze: If True, performs deep multimodal visual intelligence via Gemini 3.8 Flash
                    when GEMINI_API_KEY is present. Defaults to True.
            studio: If True, synthesizes an 8K commercial product packshot via Nano Banana Pro.
            studio_output: File path to save generated 8K studio packshot.
            studio_prompt: Custom prompt for studio packshot generation.
        """
        kind, value = classify_query(query)
        if kind == "bytes":
            res = await self.search_bytes(value)
        elif kind == "google_url":
            res = await self.search_url(value)
        elif kind == "image_url":
            res = await self.search_image_url(value)
        else:
            res = await self.search_file(value)

        if enrich:
            res = await _pro.enrich_async(res)

        accumulator = UsageAccumulator(
            default_model="gemini-3.8-flash",
            billing_tier=get_gemini_billing_tier(),
        )

        if analyze:
            analyzer = VisualAnalyzer(accumulator=accumulator)
            res.analysis = await asyncio.to_thread(
                analyzer.analyze,
                image_input=query,
                visual_matches=res.visual_matches,
                knowledge_graph=res.knowledge_graph,
                ocr_text=res.ocr_text,
            )

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
            synthesizer = StudioSynthesizer(accumulator=accumulator)
            if synthesizer.is_available:
                res.studio_asset = await asyncio.to_thread(
                    synthesizer.generate,
                    image_input=query,
                    output_path=studio_output,
                    prompt=studio_prompt,
                )

        if accumulator.get_records():
            res.cost = accumulator.to_dict()
            if res.commerce:
                res.commerce.cost = res.cost

        return res

    async def upload_image(self, image_bytes: bytes) -> str:
        """Uploads image bytes to Google Lens ingestion and returns the generated search URL (async)."""
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
            async with self._http_client(
                headers=self.config.get_headers(), follow_redirects=False
            ) as client:
                resp = await client.post(
                    LENS_UPLOAD_URL,
                    params=params,
                    files=files,  # type: ignore[arg-type]
                )
                return redirect_or_final_url(resp)
        except Exception as e:
            raise LensNetworkError(f"Failed to upload image to Google Lens: {e}") from e

    async def upload_image_url(self, image_url: str) -> str:
        """Resolves an image URL into a Google Lens search result URL (async)."""
        params = build_uploadbyurl_params(image_url, self.config.language)
        try:
            async with self._http_client(
                headers=self.config.get_headers(), follow_redirects=False
            ) as client:
                resp = await client.get(LENS_UPLOAD_BY_URL, params=params)
                return redirect_or_final_url(resp)
        except Exception as e:
            raise LensNetworkError(f"Failed to resolve image URL on Lens: {e}") from e

    async def search_bytes(self, image_bytes: bytes) -> LensSearchResult:
        """Searches using raw image bytes (async)."""
        # The Protobuf fast path and the browser search are independent; overlap them
        # so the protobuf round trip hides inside the browser's own navigation waits.
        proto_data, web_res = await asyncio.gather(
            self.protobuf_engine.process_image_bytes(image_bytes),
            self._search_image_in_browser(image_bytes),
        )

        return LensSearchResult(
            query_url=web_res.query_url,
            search_session_id=proto_data.get("search_session_id") or web_res.search_session_id,
            server_session_id=proto_data.get("server_session_id") or web_res.server_session_id,
            ocr_text=proto_data.get("ocr_text"),
            detected_objects=proto_data.get("detected_objects", []),
            visual_matches=web_res.visual_matches,
            knowledge_graph=web_res.knowledge_graph,
        )

    async def _search_image_in_browser(self, image_bytes: bytes) -> LensSearchResult:
        """Performs in-browser visual search using Playwright/Patchright with direct file input (async)."""
        async with self._browser_page() as page:
            await page.goto(
                "https://www.google.com",
                wait_until="domcontentloaded",
                timeout=self._timeout_ms,
            )
            LensParser.check_url(page.url)

            # Click the "Search by image" camera button to reveal the file input
            camera_btn = await page.wait_for_selector(
                'div[role="button"][aria-label*="Search by image"], div[aria-label*="Search by image"]',
                timeout=self._timeout_ms,
            )
            if camera_btn:
                await camera_btn.click()

            file_input = await page.wait_for_selector(
                'input[type="file"]',
                state="attached",
                timeout=self._timeout_ms,
            )
            if not file_input:
                raise LensParseError("Could not find Google Lens file upload input.")

            await file_input.set_input_files(
                {"name": "image.jpg", "mimeType": "image/jpeg", "buffer": image_bytes}
            )

            # Wait for Google to process upload and transition to search results URL
            for _ in range(max(10, int(self.config.timeout))):
                await page.wait_for_timeout(UPLOAD_POLL_INTERVAL_MS)
                if "vsrid=" in page.url:
                    break

            current_url = page.url
            LensParser.check_url(current_url)

            await self._settle(page)

            visual_matches, kg = await self._wait_for_matches(page, RESULTS_RENDER_TIMEOUT_MS)

            return LensSearchResult(
                query_url=current_url,
                visual_matches=visual_matches,
                knowledge_graph=kg,
            )

    async def search_file(self, file_path: str | Path) -> LensSearchResult:
        """Searches using a local image file (async)."""
        path = Path(file_path)
        if not path.exists():
            raise LensImageError(f"File not found: {path}")
        return await self.search_bytes(path.read_bytes())

    async def search_image_url(self, image_url: str) -> LensSearchResult:
        """Searches using a public image URL (async)."""
        image_bytes = await self._fetch_image_bytes(image_url)

        # Authenticated in-browser visual search via uploadbyurl entrypoint
        upload_url = build_uploadbyurl_url(image_url, self.config.language)

        proto_data, web_res = await asyncio.gather(
            self.protobuf_engine.process_image_bytes(image_bytes),
            self.search_url(upload_url),
        )

        return LensSearchResult(
            query_url=web_res.query_url or upload_url,
            search_session_id=proto_data.get("search_session_id"),
            server_session_id=proto_data.get("server_session_id"),
            ocr_text=proto_data.get("ocr_text"),
            detected_objects=proto_data.get("detected_objects", []),
            visual_matches=web_res.visual_matches,
            knowledge_graph=web_res.knowledge_graph,
        )

    async def search_url(self, url: str) -> LensSearchResult:
        """Fetches and parses a Google Lens search URL using Patchright async."""
        async with self._browser_page() as page:
            await page.goto(url, wait_until="domcontentloaded", timeout=self._timeout_ms)

            try:
                await page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_TIMEOUT_MS)
            except Exception:
                await page.wait_for_timeout(RENDER_FALLBACK_MS)

            LensParser.check_url(page.url)

            await self._settle(page)

            current_url = page.url
            LensParser.check_url(current_url)

            visual_matches, kg = await self._wait_for_matches(page, RESULTS_RENDER_TIMEOUT_MS)

            return LensSearchResult(
                query_url=current_url,
                visual_matches=visual_matches,
                knowledge_graph=kg,
            )

    async def _fetch_image_bytes(self, image_url: str) -> bytes:
        """Downloads raw image bytes from a public URL."""
        try:
            async with self._http_client() as client:
                resp = await client.get(
                    image_url, headers=self.config.get_headers(), follow_redirects=True
                )
                resp.raise_for_status()
                return resp.content
        except Exception as e:
            raise LensImageError(f"Failed to fetch image from URL '{image_url}': {e}") from e

    async def _resolve_to_bytes(self, query: str | Path | bytes) -> bytes:
        """Helper to convert any input into image bytes (async)."""
        if isinstance(query, bytes):
            return query
        path = Path(str(query))
        if path.exists() and path.is_file():
            return path.read_bytes()
        query_str = str(query).strip()
        if query_str.startswith(("http://", "https://")):
            return await self._fetch_image_bytes(query_str)
        raise LensConfigurationError(f"Cannot resolve '{query}' to image bytes.")
