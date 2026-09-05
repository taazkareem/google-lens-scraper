"""Chromium native protobuf engine for Google Lens (zero-CAPTCHA fast path)."""

import asyncio
import io
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from PIL import Image

try:
    from chrome_lens_py.api import LensAPI
except ImportError:
    LensAPI = None  # type: ignore

from .exceptions import LensImageError, LensNetworkError
from .models import BoundingBox, DetectedObject


class ProtobufEngine:
    """Wrapper for the Chromium native Protobuf API (lensfrontend-pa.googleapis.com)."""

    def __init__(self, proxy: str | None = None, timeout: int = 30):
        self.proxy = proxy
        self.timeout = timeout
        if LensAPI is None:
            raise ImportError(
                "chrome-lens-py is required for the native Protobuf engine. "
                "Install with 'pip install chrome-lens-py'."
            )
        self.api = LensAPI(proxy=self.proxy, timeout=self.timeout)

    async def process_image_bytes(self, image_bytes: bytes) -> dict[str, Any]:
        """Uploads image bytes to the native Protobuf endpoint and extracts OCR & session tokens."""
        try:
            # Validate that image is readable by PIL
            try:
                with Image.open(io.BytesIO(image_bytes)):
                    pass
            except Exception as e:
                raise LensImageError(f"Invalid or unreadable image bytes: {e}") from e

            res = await self.api.process_image(image_bytes)

            ocr_text = res.get("ocr_text", "")
            raw_objects = res.get("raw_response_objects")

            detected_objects: list[DetectedObject] = []
            server_session_id: str | None = None
            search_session_id: str | None = None

            if raw_objects:
                for obj in getattr(raw_objects, "overlay_objects", []):
                    bbox = None
                    if obj.HasField("geometry") and obj.geometry.HasField("bounding_box"):
                        geom = obj.geometry.bounding_box
                        bbox = BoundingBox(
                            center_x=geom.center_x,
                            center_y=geom.center_y,
                            width=geom.width,
                            height=geom.height,
                            rotation_deg=geom.rotation_z,
                        )
                    is_full = "WholeImage" in obj.id
                    detected_objects.append(
                        DetectedObject(
                            id=obj.id,
                            bounding_box=bbox,
                            is_full_image=is_full,
                        )
                    )

                if raw_objects.HasField("cluster_info"):
                    info = raw_objects.cluster_info
                    server_session_id = getattr(info, "server_session_id", None)
                    search_session_id = getattr(info, "search_session_id", None)

            # Construct direct Google Lens search URL if sessions are present
            search_url: str | None = None
            if search_session_id:
                search_url = (
                    f"https://www.google.com/search?udm=26&lns_mode=un"
                    f"&gsessionid={search_session_id}"
                )
                if server_session_id:
                    search_url += f"&lsessionid={server_session_id}"

            return {
                "ocr_text": ocr_text,
                "detected_objects": detected_objects,
                "server_session_id": server_session_id,
                "search_session_id": search_session_id,
                "search_url": search_url,
            }

        except Exception as e:
            if isinstance(e, LensImageError):
                raise
            raise LensNetworkError(f"Protobuf API request failed: {e}") from e

    def process_image_bytes_sync(self, image_bytes: bytes) -> dict[str, Any]:
        """Synchronous wrapper for process_image_bytes."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.process_image_bytes(image_bytes))

        # Called from inside a running loop (e.g. a notebook). That loop cannot drive the
        # coroutine from here, so give it a private loop on a worker thread instead.
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, self.process_image_bytes(image_bytes)).result()
