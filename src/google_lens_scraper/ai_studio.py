"""Nano Banana Pro 8K AI studio product shot synthesis engine."""

from __future__ import annotations

import io
import logging
import time
from pathlib import Path

from PIL import Image

from ._image import load_image
from .gemini_cost_calculator.accumulator import UsageAccumulator
from .models import GeneratedStudioAsset
from .settings import get_gemini_api_key

logger = logging.getLogger(__name__)

DEFAULT_STUDIO_MODEL = "models/nano-banana-pro-preview"

DEFAULT_STUDIO_PROMPT = (
    "High-resolution 8K commercial product packshot, clean editorial studio lighting, "
    "pure white seamless cyclorama background, razor-sharp focus on the item from the reference image, "
    "professional e-commerce catalog photography, 50mm macro lens, f/8, photorealistic textures, "
    "subtle soft shadow beneath product, isolated clean framing."
)


class StudioSynthesizer:
    """Synthesizes photorealistic 8K commercial catalog assets via Nano Banana Pro."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = DEFAULT_STUDIO_MODEL,
        accumulator: UsageAccumulator | None = None,
    ) -> None:
        self.api_key = api_key or get_gemini_api_key()
        self.model_name = model_name
        self.accumulator = accumulator

    @property
    def is_available(self) -> bool:
        """Returns True if an API key is present."""
        return bool(self.api_key)

    def generate(
        self,
        image_input: str | Path | bytes | Image.Image,
        output_path: str | Path | None = None,
        prompt: str | None = None,
        aspect_ratio: str = "1:1",
    ) -> GeneratedStudioAsset | None:
        """Generates an 8K studio packshot from a reference image."""
        if not self.is_available:
            logger.warning("Gemini API key not configured; cannot synthesize studio assets.")
            return None

        pil_image = load_image(image_input)
        if pil_image is None:
            logger.warning(f"Could not load reference image from: {image_input!r}")
            return None

        try:
            from google import genai
        except ImportError:
            logger.warning("google-genai package not installed; skipping studio generation.")
            return None

        client = genai.Client(api_key=self.api_key)
        final_prompt = prompt or DEFAULT_STUDIO_PROMPT

        # Determine target output path
        if output_path is None:
            timestamp = int(time.time())
            target_path = Path.cwd() / f"studio_packshot_{timestamp}.png"
        else:
            target_path = Path(output_path)

        target_path.parent.mkdir(parents=True, exist_ok=True)

        contents = [pil_image, final_prompt]

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=contents,  # type: ignore[arg-type]
            )

            # Record telemetry in accumulator if provided
            if self.accumulator is not None:
                try:
                    self.accumulator.add_call(
                        response,
                        model=self.model_name,
                        key_tag="nano_banana_studio_asset",
                    )
                except Exception as exc:
                    logger.debug(f"Cost tracking skipped for studio generation: {exc}")

            # Extract generated image bytes
            for candidate in getattr(response, "candidates", []):
                content = getattr(candidate, "content", None)
                if not content:
                    continue
                for part in getattr(content, "parts", []):
                    inline_data = getattr(part, "inline_data", None)
                    if inline_data and getattr(inline_data, "data", None):
                        data_bytes = inline_data.data
                        # If base64 encoded string, decode; if already bytes, load directly
                        if isinstance(data_bytes, str):
                            import base64

                            data_bytes = base64.b64decode(data_bytes)

                        img = Image.open(io.BytesIO(data_bytes))
                        img.save(str(target_path))
                        logger.info(f"Synthesized studio asset saved to {target_path}")

                        return GeneratedStudioAsset(
                            image_path=str(target_path.resolve()),
                            prompt_used=final_prompt,
                            aspect_ratio=aspect_ratio,
                            model=self.model_name,
                        )

            logger.warning("No image data found in Nano Banana generation response.")
            return None

        except Exception as exc:
            logger.warning(f"Nano Banana studio generation failed: {exc}")
            return None
