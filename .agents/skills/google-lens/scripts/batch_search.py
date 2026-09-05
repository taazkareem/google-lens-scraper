#!/usr/bin/env python3
# /// script
# dependencies = [
#   "google-lens-scraper",
# ]
# ///
"""Standalone batch-search script for processing multiple images via Google Lens."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from google_lens_scraper import AsyncLensScraper, LensConfig

VALID_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}


async def process_item(
    scraper: AsyncLensScraper,
    query: str,
    ocr_only: bool,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    async with semaphore:
        try:
            if ocr_only:
                res = await scraper.detect(query)
            else:
                res = await scraper.search(query)
            return {"query": query, "status": "success", "data": res.to_dict()}
        except Exception as exc:
            return {"query": query, "status": "error", "error": str(exc)}


async def run_batch(
    queries: list[str],
    concurrency: int,
    ocr_only: bool,
    output_file: str | None,
) -> None:
    config = LensConfig(headless=True)
    scraper = AsyncLensScraper(config=config)
    semaphore = asyncio.Semaphore(concurrency)

    sys.stderr.write(
        f"Starting batch search for {len(queries)} items (concurrency={concurrency})...\n"
    )

    tasks = [process_item(scraper, q, ocr_only, semaphore) for q in queries]
    results = await asyncio.gather(*tasks)

    payload = {
        "total": len(queries),
        "results": results,
    }
    out_str = json.dumps(payload, indent=2)

    if output_file:
        Path(output_file).write_text(out_str, encoding="utf-8")
        sys.stderr.write(f"Batch completed. Results saved to {output_file}\n")
    else:
        print(out_str)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch process multiple images or URLs through Google Lens."
    )
    parser.add_argument("queries", nargs="*", help="Optional list of image URLs or file paths")
    parser.add_argument("--dir", type=str, help="Directory containing images to process")
    parser.add_argument(
        "--urls-file", type=str, help="Path to text file containing URLs (one per line)"
    )
    parser.add_argument(
        "--ocr-only", action="store_true", help="Extract OCR only (faster, no browser)"
    )
    parser.add_argument(
        "--concurrency", type=int, default=2, help="Number of concurrent searches (default: 2)"
    )
    parser.add_argument("--output", "-o", type=str, help="Path to output JSON file")

    args = parser.parse_args()

    items: list[str] = list(args.queries)

    if args.urls_file:
        p = Path(args.urls_file)
        if not p.exists():
            sys.stderr.write(f"Error: URLs file '{args.urls_file}' not found.\n")
            sys.exit(1)
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                items.append(line)

    if args.dir:
        dp = Path(args.dir)
        if not dp.is_dir():
            sys.stderr.write(f"Error: Directory '{args.dir}' not found.\n")
            sys.exit(1)
        for f in dp.iterdir():
            if f.is_file() and f.suffix.lower() in VALID_EXTENSIONS:
                items.append(str(f.resolve()))

    if not items:
        sys.stderr.write("No images or URLs provided. Specify queries, --dir, or --urls-file.\n")
        parser.print_help(sys.stderr)
        sys.exit(1)

    asyncio.run(run_batch(items, args.concurrency, args.ocr_only, args.output))


if __name__ == "__main__":
    main()
