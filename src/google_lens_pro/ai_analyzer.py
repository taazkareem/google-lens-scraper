"""Multimodal visual intelligence engine powered by Gemini 3.8 Flash."""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from PIL import Image

from ._image import load_image
from .gemini_cost_calculator.accumulator import UsageAccumulator
from .models import (
    KnowledgeGraph,
    ProductAttributes,
    VisualAnalysis,
    VisualMatch,
)
from .settings import get_gemini_api_key

logger = logging.getLogger(__name__)

DEFAULT_ANALYSIS_MODEL = "gemini-3.8-flash"

ANALYSIS_SYSTEM_INSTRUCTION = """You are an expert product authenticator, commercial appraiser, and visual commerce intelligence analyst.
Analyze the provided image in conjunction with any detected visual match metadata.

Produce an exhaustive, highly structured visual analysis with:
1. summary: A professional, concise 1-2 sentence executive identification.
2. attributes:
   - brand: Identified manufacturer or luxury house.
   - model_or_name: Precise model name, silhouette, or product line.
   - category: Specific product category.
   - color: Colorway or finish.
   - materials: Identified fabrics, metals, leathers, or composites.
   - condition_assessment: Visual condition (e.g., 'Brand New / Deadstock', 'Excellent Pre-Owned', 'Vintage Good').
   - key_features: 3-5 distinctive design elements, stitching, hardware, or tech specs.
   - authenticity_markers: Specific visual cues used for authentication.
   - estimated_msrp_usd: Estimated original retail price in USD as a number, or null.
   - confidence_score: Confidence rating between 0.0 and 1.0.
3. match_evaluations: For each numbered candidate visual match provided in the prompt, classify its relevance:
   - index: The 0-based integer index of the candidate match.
   - relevance: Exactly one of:
       * "exact_match": Listing is selling or showcasing the identical product, silhouette, and model seen in the image.
       * "similar": Alternative model from the same brand or a competing product in the same category.
       * "reference": Editorial article, review, photo portfolio, educational document, or printable worksheet.
       * "unrelated": Completely different product category, accessory, theme demo, or irrelevant noise.
   - reason: A concise 1-sentence explanation of why it was classified this way.
4. resale_recommendation: Market velocity, price arbitrage outlook, or resale advice.
5. tags: 5-10 descriptive search and cataloging tags.
"""


def _format_context_prompt(
    visual_matches: Sequence[VisualMatch] | None = None,
    knowledge_graph: KnowledgeGraph | None = None,
    ocr_text: str | None = None,
) -> str:
    """Builds an informative text prompt from Google Lens search metadata."""
    parts = ["Perform deep visual intelligence and product attribute extraction on this image."]

    if knowledge_graph and knowledge_graph.title:
        parts.append(f"\n[Google Knowledge Graph]: {knowledge_graph.title}")
        if knowledge_graph.subtitle:
            parts.append(f" - {knowledge_graph.subtitle}")
        if knowledge_graph.description:
            parts.append(f"\nDescription: {knowledge_graph.description}")

    if ocr_text:
        cleaned_ocr = ocr_text.strip()
        if cleaned_ocr:
            parts.append(f"\n[OCR Text Detected in Image]:\n{cleaned_ocr[:500]}")

    if visual_matches:
        candidate_matches = list(visual_matches[:25])
        parts.append("\n[Candidate Visual Matches to Classify]:")
        for idx, m in enumerate(candidate_matches):
            price_info = f" ({m.price})" if m.price else ""
            source_info = f" on {m.source}" if m.source else ""
            parts.append(f"  [{idx}]: {m.title}{price_info}{source_info}")

    return "\n".join(parts)


_GENERIC_SERP_TITLES = {
    "search results",
    "search result",
    "visual matches",
    "visual match",
    "more results",
    "related images",
    "results for images",
    "image results",
    "all",
    "products",
    "images",
    "search",
    "web results",
    "similar images",
}


def deduce_native_analysis(
    visual_matches: Sequence[VisualMatch] | None = None,
    knowledge_graph: KnowledgeGraph | None = None,
    ocr_text: str | None = None,
) -> VisualAnalysis | None:
    """Extracts baseline structured product attributes dynamically from Google Lens metadata without external API keys or hardcoded brand lists."""
    title: str | None = None
    category: str | None = None
    brand: str | None = None

    # 1. Filter out boilerplate SERP headings in KnowledgeGraph
    if knowledge_graph:
        if (
            knowledge_graph.subtitle
            and knowledge_graph.subtitle.strip().lower() not in _GENERIC_SERP_TITLES
            and len(knowledge_graph.subtitle.strip()) > 1
        ):
            category = knowledge_graph.subtitle.strip()

        if knowledge_graph.title:
            cand = knowledge_graph.title.strip()
            if cand.lower() not in _GENERIC_SERP_TITLES and len(cand) > 2:
                title = cand

    # 2. Extract OCR tokens if available for dynamic cross-referencing
    ocr_tokens: set[str] = set()
    if ocr_text:
        ocr_tokens = {t for t in re.findall(r"[a-z0-9]+", ocr_text.lower()) if len(t) > 2}

    best_match: VisualMatch | None = None

    # 3. If no entity card, select the best visual match dynamically
    if not title and visual_matches:
        valid_candidates: list[tuple[int, int, VisualMatch]] = []
        for idx, m in enumerate(visual_matches):
            if not m.title or m.title.strip().lower() in _GENERIC_SERP_TITLES or len(m.title) <= 3:
                continue

            # Calculate token intersection with OCR text
            title_tokens = {t for t in re.findall(r"[a-z0-9]+", m.title.lower()) if len(t) > 2}
            overlap = len(ocr_tokens.intersection(title_tokens)) if ocr_tokens else 0
            # Sort priority: highest OCR overlap first, then Google Lens rank order (lowest index)
            valid_candidates.append((overlap, -idx, m))

        if valid_candidates:
            best_match = max(valid_candidates, key=lambda x: (x[0], x[1]))[2]
            title = best_match.title

    if not title:
        return None

    clean_title = title
    if best_match:
        source_candidates: set[str] = set()
        if best_match.source:
            source_candidates.add(best_match.source.strip())
        if best_match.link:
            host = urlparse(best_match.link).netloc.lower().replace("www.", "")
            if host:
                source_candidates.add(host)
                sld = host.split(".")[0]
                if len(sld) > 2:
                    source_candidates.add(sld)

        for src in sorted(source_candidates, key=len, reverse=True):
            clean_title = re.sub(
                rf"\s*[-|•:–—]\s*{re.escape(src)}.*$",
                "",
                clean_title,
                flags=re.I,
            ).strip()

    # Clean trailing domain extensions (e.g. " - store.com")
    clean_title = re.sub(
        r"\s*[-|•:–—]\s*[a-z0-9\s.-]+\.(?:com|org|net|co|io|uk|de|shop|store|ca|app|me).*$",
        "",
        clean_title,
        flags=re.I,
    ).strip()

    # Clean any dangling separator characters at the end of the title
    clean_title = re.sub(r"\s*[-|•:–—]\s*$", "", clean_title).strip()
    if not clean_title:
        clean_title = title

    # 4. Extract Brand dynamically:
    # Check if any leading word in clean_title matches an OCR token
    words = clean_title.split()
    if words:
        for w in words[:3]:
            clean_w = re.sub(r"[^\w]", "", w)
            if clean_w.lower() in ocr_tokens and len(clean_w) > 1:
                brand = clean_w
                break

        # Fallback to the leading capitalized word of the title (standard in commerce titles)
        if not brand:
            first_word = re.sub(r"[^\w]", "", words[0])
            if len(first_word) > 1 and first_word.lower() not in _GENERIC_SERP_TITLES:
                brand = first_word

    attributes = ProductAttributes(
        brand=brand,
        model_or_name=clean_title,
        category=category,
        confidence_score=0.85,
    )

    tags = [t.lower() for t in clean_title.split() if len(t) > 3][:6]

    return VisualAnalysis(
        summary=f"Identified item: {clean_title}" + (f" ({category})" if category else ""),
        attributes=attributes,
        resale_recommendation="Review verified merchant pricing in visual matches for current market value.",
        tags=tags,
    )


class VisualAnalyzer:
    """Multimodal analyzer utilizing Gemini 3.8 Flash to extract deep attributes and commerce insights."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = DEFAULT_ANALYSIS_MODEL,
        accumulator: UsageAccumulator | None = None,
    ) -> None:
        self.api_key = api_key or get_gemini_api_key()
        self.model_name = model_name
        self.accumulator = accumulator

    @property
    def is_available(self) -> bool:
        """Returns True if an API key is present."""
        return bool(self.api_key)

    def analyze(
        self,
        image_input: str | Path | bytes | Image.Image,
        visual_matches: Sequence[VisualMatch] | None = None,
        knowledge_graph: KnowledgeGraph | None = None,
        ocr_text: str | None = None,
    ) -> VisualAnalysis | None:
        """Analyzes an image and returns structured VisualAnalysis."""
        if not self.is_available:
            return deduce_native_analysis(
                visual_matches=visual_matches,
                knowledge_graph=knowledge_graph,
                ocr_text=ocr_text,
            )

        pil_image = load_image(image_input)
        if pil_image is None:
            logger.warning(f"Could not load image from input: {image_input!r}")
            return None

        try:
            from google import genai
            from google.genai import types
        except ImportError:
            logger.warning("google-genai package not installed; skipping AI visual analysis.")
            return None

        client = genai.Client(api_key=self.api_key)
        prompt = _format_context_prompt(
            visual_matches=visual_matches,
            knowledge_graph=knowledge_graph,
            ocr_text=ocr_text,
        )

        contents = [pil_image, prompt]

        config_kwargs: dict[str, Any] = {
            "system_instruction": ANALYSIS_SYSTEM_INSTRUCTION,
            "response_mime_type": "application/json",
            "response_schema": VisualAnalysis,
            "temperature": 0.2,
        }
        if hasattr(types, "AutomaticFunctionCallingConfig"):
            config_kwargs["automatic_function_calling"] = types.AutomaticFunctionCallingConfig(
                disable=True
            )
        config = types.GenerateContentConfig(**config_kwargs)

        last_exc: Exception | None = None
        for candidate_model in dict.fromkeys(
            [self.model_name, "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash"]
        ):
            for attempt in range(2):
                try:
                    response = client.models.generate_content(
                        model=candidate_model,
                        contents=contents,  # type: ignore[arg-type]
                        config=config,
                    )

                    # Record telemetry in accumulator if provided
                    if self.accumulator is not None:
                        try:
                            self.accumulator.add_call(
                                response,
                                model=candidate_model,
                                key_tag="gemini_visual_analysis",
                            )
                        except Exception as exc:
                            logger.debug(f"Cost tracking skipped for visual analysis: {exc}")

                    # Extract structured response
                    if hasattr(response, "parsed") and isinstance(response.parsed, VisualAnalysis):
                        return response.parsed

                    # Fallback to parsing text
                    raw_text = getattr(response, "text", "") or ""
                    if raw_text:
                        data = json.loads(raw_text)
                        return VisualAnalysis.model_validate(data)

                    # Empty (non-error) response — no value in retrying other models
                    break

                except Exception as exc:
                    last_exc = exc
                    err_str = str(exc)
                    # On transient 503/429 spike on first attempt, back off briefly and retry once
                    if attempt == 0 and any(
                        code in err_str
                        for code in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED")
                    ):
                        logger.debug(
                            f"Transient error on {candidate_model} ({exc}); retrying in 1s..."
                        )
                        time.sleep(1.0)
                        continue

                    logger.debug(
                        f"Gemini visual analysis failed on {candidate_model} ({exc}); trying next if available."
                    )
                    break

        logger.warning(
            f"Gemini visual analysis failed ({last_exc}); falling back to native deduction."
        )
        return deduce_native_analysis(
            visual_matches=visual_matches,
            knowledge_graph=knowledge_graph,
            ocr_text=ocr_text,
        )
