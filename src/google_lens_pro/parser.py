"""HTML and JavaScript array parser for Google Lens responses."""

import json
import re
from typing import Any
from urllib.parse import urlparse

from .exceptions import LensParseError, LensRateLimitError
from .models import KnowledgeGraph, VisualMatch

# Obfuscated Google result-card class names. Google rotates these, so keeping them
# in one place makes a rename a single-line change for the parser and both clients.
CARD_CONTAINER_CLASS = "N54PNb"
VISUAL_MATCH_SELECTOR = f"a.LBcIee, div[data-item-id], div.{CARD_CONTAINER_CLASS}"

# How far up the DOM to climb from an anchor when looking for its enclosing result card.
MAX_CONTAINER_CLIMB = 4

# A block/CAPTCHA challenge page is small; a real SERP is huge and its inline JS
# happens to reference '/sorry/index' without being a challenge.
MAX_CHALLENGE_PAGE_BYTES = 50_000

# Console-script name from [project.scripts] in pyproject.toml. Centralized here (rather
# than repeated across CLI help strings) so a rename is a single-line change.
PROG_NAME = "google-lens"

_AF_INIT_PATTERN = re.compile(
    r"AF_initDataCallback\s*\(\s*\{[^\}]*?data:\s*(\[.*?\])\s*,\s*sideChannel",
    re.DOTALL,
)
_LINK_PATTERN = re.compile(
    r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>',
    re.DOTALL | re.IGNORECASE,
)
_IMG_SRC_PATTERN = re.compile(r'<img[^>]+src="([^"]+)"', re.IGNORECASE)
_TAG_PATTERN = re.compile(r"<[^>]+>")

# Recognized currency symbols/codes. Shared with commerce.py's PriceNormalizer so the two
# price detectors can't silently drift apart on which currencies they recognize.
CURRENCY_TOKEN_PATTERN = r"[\$€£¥₹]|USD|EUR|GBP|CAD|AUD|INR"
_PRICE_PATTERN = re.compile(
    rf"(?:{CURRENCY_TOKEN_PATTERN})\s*\d+(?:[,\.]\d+)*(?:\s*(?:USD|EUR|GBP|CAD|AUD|INR))?"
    rf"|(?:\d+(?:[,\.]\d+)*\s*(?:{CURRENCY_TOKEN_PATTERN}))",
    re.IGNORECASE,
)
_ENTITY_NAME_PATTERN = re.compile(r'data-entityname="([^"]+)"', re.IGNORECASE)
_H1_PATTERN = re.compile(r"<h1[^>]*>([^<]+)</h1>", re.IGNORECASE)

_BLOCKED_HELP = (
    "Google blocked the session from this network. "
    f"Run '{PROG_NAME} login' to sign into your Google account once, "
    "or specify a residential proxy (--proxy)."
)


class LensParser:
    """Parses Google Lens search result pages from DOM and hydration payloads."""

    @staticmethod
    def check_url(url: str) -> None:
        """Raises if a navigation landed on a Google block page or bounced to the homepage."""
        if "sorry/index" in url:
            raise LensRateLimitError(
                f"Google Lens rate limit / bot detection triggered (/sorry/index). {_BLOCKED_HELP}",
                status_code=429,
            )
        if "google.com/webhp" in url:
            raise LensParseError(
                "Google redirected visual search to homepage (webhp). "
                "The image search tokens or interaction data were rejected.",
            )

    @staticmethod
    def check_html(html: str) -> None:
        """Raises if a rendered page is a Google block / CAPTCHA challenge."""
        if "sorry/index" in html and len(html) < MAX_CHALLENGE_PAGE_BYTES:
            raise LensRateLimitError(
                f"Google Lens rate limit / bot detection triggered (/sorry/index). {_BLOCKED_HELP}",
                status_code=429,
            )
        if "Our systems have detected unusual traffic" in html or '<div id="recaptcha"' in html:
            raise LensRateLimitError(
                f"Google Lens rate limit / bot detection triggered (unusual traffic). "
                f"{_BLOCKED_HELP}",
                status_code=429,
            )

    @classmethod
    def parse_html(cls, html: str) -> tuple[list[VisualMatch], KnowledgeGraph | None]:
        """Extracts visual matches and knowledge graph data from HTML string."""
        cls.check_html(html)

        # Strategies in descending order of fidelity; the first to yield matches wins.
        strategies = (
            cls.extract_from_dom_cards,  # rendered DOM cards (live browser searches)
            cls.extract_from_af_init,  # embedded AF_initDataCallback payloads
            cls.extract_from_raw_html_regex,  # regex heuristics over raw HTML
        )

        matches: list[VisualMatch] = []
        for strategy in strategies:
            matches = cls._dedupe_by_link(strategy(html))
            if matches:
                break

        return matches, cls.extract_knowledge_graph(html)

    @staticmethod
    def _dedupe_by_link(matches: list[VisualMatch]) -> list[VisualMatch]:
        """Keeps the first match per destination link, dropping entries without one."""
        seen: set[str] = set()
        deduped: list[VisualMatch] = []
        for m in matches:
            if m.link and m.link not in seen:
                seen.add(m.link)
                deduped.append(m)
        return deduped

    @classmethod
    def extract_from_dom_cards(cls, html_content: str) -> list[VisualMatch]:
        """Extracts visual matches from rendered Google Lens DOM cards using lxml."""
        from lxml import html

        matches: list[VisualMatch] = []
        try:
            tree = html.fromstring(html_content)
        except Exception:
            return matches

        seen_urls: set[str] = set()
        for a in tree.xpath(
            '//a[@href and not(contains(@href, "google.com")) and not(contains(@href, "gstatic.com"))]'
        ):
            href = a.get("href", "").strip()
            if not href.startswith("http") or href in seen_urls:
                continue

            container = a
            for _ in range(MAX_CONTAINER_CLIMB):
                p = container.getparent()
                if p is None:
                    break
                container = p
                if (
                    p.get("class", "").startswith(CARD_CONTAINER_CLASS)
                    or p.get("data-snc")
                    or "card" in p.get("class", "").lower()
                ):
                    break

            text_blocks = [t.strip() for t in a.itertext() if t.strip()]
            if not text_blocks:
                continue

            source = text_blocks[0] if len(text_blocks) > 1 else ""
            title = text_blocks[1] if len(text_blocks) > 1 else text_blocks[0]

            # container is `a` itself or an ancestor climbed to above, so its itertext()
            # already includes the anchor's own text in document order.
            price = None
            for ct in container.itertext():
                m = _PRICE_PATTERN.search(ct.strip())
                if m:
                    price = m.group(0)
                    break

            thumb = None
            for img in container.xpath(".//img"):
                src = img.get("src") or img.get("data-src") or ""
                if src.startswith("data:image/jpeg") or "http" in src:
                    thumb = src
                    break
                if src.startswith("data:image/") and not thumb:
                    thumb = src

            if title and len(title) > 2:
                seen_urls.add(href)
                matches.append(
                    VisualMatch(
                        title=title,
                        link=href,
                        source=source,
                        thumbnail=thumb,
                        price=price,
                    )
                )

        return matches

    @classmethod
    def extract_from_af_init(cls, html: str) -> list[VisualMatch]:
        """Extracts visual matches from AF_initDataCallback JavaScript blobs."""
        matches: list[VisualMatch] = []
        for block in _AF_INIT_PATTERN.findall(html):
            try:
                data = json.loads(block)
            except Exception:
                continue
            cls._walk_af_tree(data, matches)

        return matches

    @classmethod
    def _walk_af_tree(cls, node: Any, matches: list[VisualMatch]) -> None:
        """Recursive structure-matching heuristic for Google Lens result arrays."""
        if isinstance(node, list):
            urls = [
                x
                for x in node
                if isinstance(x, str) and (x.startswith("http://") or x.startswith("https://"))
            ]
            has_thumbnail = any("encrypted-tbn" in u or "gstatic.com" in u for u in urls)
            external_urls = [
                u
                for u in urls
                if not ("google.com" in u or "gstatic.com" in u or "googleapis.com" in u)
            ]

            if has_thumbnail and external_urls:
                target_url = external_urls[0]
                thumb_url = next(
                    (u for u in urls if "encrypted-tbn" in u or "gstatic.com" in u),
                    None,
                )

                strings = [
                    s.strip()
                    for s in node
                    if isinstance(s, str) and s not in urls and len(s.strip()) > 1
                ]

                title = strings[0] if strings else ""
                source = strings[1] if len(strings) > 1 else ""
                if not source and target_url:
                    source = urlparse(target_url).netloc.replace("www.", "")

                price = next((s for s in strings if _PRICE_PATTERN.search(s)), None)

                matches.append(
                    VisualMatch(
                        title=title,
                        link=target_url,
                        thumbnail=thumb_url,
                        source=source,
                        price=price,
                    )
                )
                return

            for child in node:
                cls._walk_af_tree(child, matches)

    @classmethod
    def is_external_link(cls, url: str) -> bool:
        """Determines if a URL is an external destination rather than Google internal infra."""
        try:
            domain = urlparse(url).netloc.lower()
            if not domain:
                return False
            ignored_domains = (
                "google.com",
                "google.",
                "ai.google",
                "gstatic.com",
                "googleapis.com",
                "googleusercontent.com",
                "schema.org",
                "w3.org",
            )
            return not any(ign in domain for ign in ignored_domains)
        except Exception:
            return False

    @classmethod
    def extract_from_raw_html_regex(cls, html: str) -> list[VisualMatch]:
        """Regex-based fallback extraction when JavaScript AST is compressed."""
        matches: list[VisualMatch] = []

        for match in _LINK_PATTERN.finditer(html):
            url = match.group(1)
            body = match.group(2)

            if not cls.is_external_link(url):
                continue

            img_match = _IMG_SRC_PATTERN.search(body)
            thumb = img_match.group(1) if img_match else None

            clean_text = " ".join(_TAG_PATTERN.sub(" ", body).split()).strip()

            # A legitimate visual match must have an associated image thumbnail
            if thumb and len(clean_text) > 2:
                source = urlparse(url).netloc.replace("www.", "")
                matches.append(
                    VisualMatch(
                        title=clean_text or source,
                        link=url,
                        thumbnail=thumb,
                        source=source,
                    )
                )

        return matches

    @classmethod
    def extract_knowledge_graph(cls, html: str) -> KnowledgeGraph | None:
        """Attempts to extract the identified entity from Google's Knowledge Graph section."""
        m = _ENTITY_NAME_PATTERN.search(html)
        if m:
            return KnowledgeGraph(title=m.group(1))

        # Fall back to a prominent title in the about-this-image / entity header
        h1_m = _H1_PATTERN.search(html)
        if h1_m and "Google" not in h1_m.group(1):
            return KnowledgeGraph(title=h1_m.group(1).strip())

        return None
