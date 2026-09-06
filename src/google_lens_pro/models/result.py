"""SPDX-FileCopyrightText: © 2026 Talib Kareem <taazkareem@icloud.com>
SPDX-License-Identifier: MIT

Unified search result model across Google Lens and Google Shopping.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from pydantic import BaseModel, Field

from .commerce import CommerceIntelligence, GeneratedStudioAsset, VisualAnalysis
from .lens import DetectedObject, KnowledgeGraph, VisualMatch
from .shopping import ShoppingResult


class LensSearchResult(BaseModel):
    """Structured response from a Google Lens or Unified Fusion search."""

    query_url: str | None = Field(default=None, description="The Google search URL executed")
    search_session_id: str | None = Field(default=None, description="Google gsessionid token")
    server_session_id: str | None = Field(default=None, description="Google lsessionid token")
    ocr_text: str | None = Field(default=None, description="Full OCR text extracted from the image")
    detected_objects: list[DetectedObject] = Field(
        default_factory=list, description="Visual objects found"
    )
    visual_matches: list[VisualMatch] = Field(
        default_factory=list, description="List of matching web items"
    )
    shopping: ShoppingResult | None = Field(
        default=None, description="Direct Google Shopping offers and price comparisons"
    )
    knowledge_graph: KnowledgeGraph | None = Field(default=None, description="Knowledge Graph card")
    commerce: CommerceIntelligence | None = Field(
        default=None, description="Pro E-Commerce and Resale Arbitrage intelligence"
    )
    analysis: VisualAnalysis | None = Field(
        default=None, description="Multimodal visual intelligence via Gemini 3.8 Flash"
    )
    studio_asset: GeneratedStudioAsset | None = Field(
        default=None, description="Synthesized 8K commercial catalog asset via Nano Banana Pro"
    )
    cost: dict[str, Any] | None = Field(
        default=None, description="Detailed Gemini token usage and financial cost telemetry"
    )

    def to_dict(self) -> dict[str, Any]:
        """Serializes the result to a clean Python dictionary."""
        return self.model_dump(exclude_none=True)

    def to_json(self, indent: int = 2) -> str:
        """Serializes the result to a formatted JSON string."""
        return self.model_dump_json(indent=indent, exclude_none=True)

    def __len__(self) -> int:
        """Returns the number of visual matches."""
        return len(self.visual_matches)

    def iter_matches(self) -> Iterator[VisualMatch]:
        """Iterates over visual matches."""
        return iter(self.visual_matches)

    def __getitem__(self, index: int) -> VisualMatch:
        """Allows direct indexing into visual matches."""
        return self.visual_matches[index]
