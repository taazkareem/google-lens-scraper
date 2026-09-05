"""Multimodal visual intelligence engine powered by Gemini 3.8 Flash."""

from __future__ import annotations

import io
import json
import logging
import re
from collections.abc import Sequence
from pathlib import Path

from PIL import Image

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
3. resale_recommendation: Market velocity, price arbitrage outlook, or resale advice.
4. tags: 5-10 descriptive search and cataloging tags.
"""


def _load_image(image_input: str | Path | bytes | Image.Image) -> Image.Image | None:
    """Loads an image into a PIL Image instance."""
    if isinstance(image_input, Image.Image):
        return image_input
    if isinstance(image_input, (str, Path)):
        p = Path(image_input)
        if p.exists() and p.is_file():
            return Image.open(p)
        return None
    if isinstance(image_input, bytes):
        return Image.open(io.BytesIO(image_input))
    return None


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
        top_matches = list(visual_matches[:6])
        parts.append("\n[Top Web Visual Matches]:")
        for idx, m in enumerate(top_matches, 1):
            price_info = f" ({m.price})" if m.price else ""
            source_info = f" on {m.source}" if m.source else ""
            parts.append(f"  {idx}. {m.title}{price_info}{source_info}")

    return "\n".join(parts)


def deduce_native_analysis(
    visual_matches: Sequence[VisualMatch] | None = None,
    knowledge_graph: KnowledgeGraph | None = None,
    ocr_text: str | None = None,
) -> VisualAnalysis | None:
    """Extracts baseline structured product attributes directly from Google Lens metadata without external API keys."""
    title = None
    category = None
    brand = None

    if knowledge_graph and knowledge_graph.title:
        title = knowledge_graph.title
        category = knowledge_graph.subtitle
    elif visual_matches:
        for m in visual_matches:
            if m.title and len(m.title) > 3:
                title = m.title
                break

    if not title:
        return None

    # Brand heuristics for instant identification
    known_brands = [
        "Nike",
        "Adidas",
        "Jordan",
        "New Balance",
        "Puma",
        "Asics",
        "Yeezy",
        "Apple",
        "Sony",
        "Samsung",
        "Google",
        "Dell",
        "Bose",
        "Sennheiser",
        "Rolex",
        "Omega",
        "Seiko",
        "Casio",
        "Cartier",
        "Breitling",
        "Patek Philippe",
        "Gucci",
        "Prada",
        "Louis Vuitton",
        "Balenciaga",
        "Saint Laurent",
        "Dior",
        "Lego",
        "Nintendo",
        "PlayStation",
        "Xbox",
        "Pokemon",
    ]
    for b in known_brands:
        if b.lower() in title.lower():
            brand = b
            break

    if not brand and " " in title:
        first_token = title.split()[0].rstrip(":,.-")
        if len(first_token) > 2 and first_token.istitle():
            brand = first_token

    clean_title = re.sub(
        r"\s*[-|•]\s*(?:GOAT|eBay|StockX|Amazon|Walmart|TheRealReal|Grailed|SeedProd|WooLentor).*$",
        "",
        title,
        flags=re.I,
    ).strip()

    attributes = ProductAttributes(
        brand=brand,
        model_or_name=clean_title,
        category=category or "Product / Merchandise",
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

        pil_image = _load_image(image_input)
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

        config = types.GenerateContentConfig(
            system_instruction=ANALYSIS_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=VisualAnalysis,
            temperature=0.2,
        )

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=contents,  # type: ignore[arg-type]
                config=config,
            )

            # Record telemetry in accumulator if provided
            if self.accumulator is not None:
                try:
                    self.accumulator.add_call(
                        response,
                        model=self.model_name,
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

            return deduce_native_analysis(
                visual_matches=visual_matches,
                knowledge_graph=knowledge_graph,
                ocr_text=ocr_text,
            )

        except Exception as exc:
            logger.warning(
                f"Gemini visual analysis failed ({exc}); falling back to native deduction."
            )
            return deduce_native_analysis(
                visual_matches=visual_matches,
                knowledge_graph=knowledge_graph,
                ocr_text=ocr_text,
            )
