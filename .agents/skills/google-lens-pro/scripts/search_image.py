#!/usr/bin/env python3
# /// script
# dependencies = [
#   "google-lens-pro",
# ]
# ///
"""Standalone single-image search script with filtering support for Agent Skills."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from google_lens_pro import LensConfig, LensScraper


def parse_price(price_str: str | None) -> float | None:
    """Extract numeric value from currency strings like '$129.99' or '€ 45.00'."""
    if not price_str:
        return None
    match = re.search(r"[\d]+(?:[.,]\d{2})?", price_str.replace(",", ""))
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return None
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search Google Lens for an image and filter structured results."
    )
    parser.add_argument("query", help="Image URL or local file path")
    parser.add_argument(
        "--ocr-only",
        action="store_true",
        help="Run fast Protobuf OCR and object detection only (no browser)",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=None,
        help="Maximum number of visual matches to return",
    )
    parser.add_argument(
        "--min-price",
        type=float,
        default=None,
        help="Filter visual matches with price at or above this threshold",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Print raw JSON to stdout",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Save filtered JSON output to specified file path",
    )

    args = parser.parse_args()

    config = LensConfig(headless=True)
    scraper = LensScraper(config=config)

    try:
        result = scraper.detect(args.query) if args.ocr_only else scraper.search(args.query)
    except Exception as exc:
        sys.stderr.write(f"Error querying Google Lens: {exc}\n")
        sys.exit(1)

    data: dict[str, Any] = result.to_dict()

    # Apply visual matches filtering if requested
    matches = data.get("visual_matches", [])
    if args.min_price is not None:
        filtered = []
        for m in matches:
            val = parse_price(m.get("price"))
            if val is not None and val >= args.min_price:
                filtered.append(m)
        matches = filtered

    if args.max_results is not None:
        matches = matches[: args.max_results]

    data["visual_matches"] = matches

    out_str = json.dumps(data, indent=2)

    if args.output:
        Path(args.output).write_text(out_str, encoding="utf-8")
        sys.stderr.write(f"Results saved to {args.output}\n")

    if args.json_output or not args.output:
        print(out_str)


if __name__ == "__main__":
    main()
