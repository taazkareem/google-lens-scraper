---
name: google-lens-pro
description: Search Google Lens to find visual matches, identify products and prices, extract text with OCR, and recognize entities (landmarks, plants, artwork). Use when asked to reverse image search, identify items in an image, find where to buy a product, or extract text from photos.
license: MIT
compatibility: Requires Python 3.10+ and google-lens-pro package
metadata:
  author: taazkareem
  version: "0.2.0"
---

# Google Lens Pro Agent Skill

This skill allows an AI agent to execute reverse image searches, extract optical character recognition (OCR) text, detect visual entities, and find shopping matches/prices via Google Lens.

## Prerequisites & Installation

If `lens` is not yet installed in the environment, install the package and download the stealth Chromium browser binary:

```bash
pip install google-lens-pro
patchright install chromium
```

> **Note:** Fast-path OCR mode (`--ocr-only`) only requires the Python package and works immediately without downloading Chromium binaries.

## Quick Start Recipes

### 1. Reverse Image Search & Visual Intelligence (Default Mode)
To find matching products, web sources, normalized pricing analytics, and multimodal attribute analysis:

```bash
google-lens search "<image-url-or-path>" --json-output
```

*Note: By default, `google-lens search` automatically executes e-commerce price normalization (`--enrich`) and deep multimodal attribute analysis (`--analyze`) via Gemini 3.8 Flash if `GEMINI_API_KEY` is present.*

> **Agent In-Context Fallback Strategy**: If `results.analysis` is `null` (because `GEMINI_API_KEY` is not configured in the host environment), **you (the AI Agent)** should inspect the query image and the returned `visual_matches` directly within your own conversation context to deduce product attributes (brand, model silhouette, materials, condition, estimated MSRP, authenticity cues). This guarantees zero friction for users without requiring additional API keys.

### 2. Nano Banana Pro 8K AI Studio Packshot Generation
To synthesize an ultra-crisp 8K commercial catalog packshot on a pristine white background from a reference image:

```bash
google-lens search "<image-url-or-path>" --studio --studio-output ./packshot.png
```

You can optionally provide a custom prompt:
```bash
google-lens search "<image-url-or-path>" --studio --studio-prompt "8K studio catalog shot on black brushed granite with soft dramatic rim lighting"
```

### 3. Fast-Path OCR & Object Detection (Sub-second, No CAPTCHA)
For extracting text or bounding boxes from an image (uses Chromium Protobuf endpoint, zero browser overhead):

```bash
google-lens search "<image-url-or-path>" --ocr-only --json-output
```

### 4. E-Commerce & Resale Arbitrage Intelligence (Pro)
To resolve clean canonical URLs, normalized price ranges (min/max/average), semantic match relevance, and identify the lowest-priced verified seller ("Best Deal"):

```bash
google-lens search "<image-url-or-path>" --enrich --json-output
```

Pro enrichment categorizes candidates against the identified `target_product` using Gemini 3.8 Flash into universal semantic classes:
- `exact_match`: Exact physical product match (eligible for price comparison and Best Deal).
- `similar`: Same silhouette, competing brand, or variant edition.
- `reference`: Blog reviews, worksheets, wallpapers, or editorial context.
- `unrelated`: Incompatible accessories, third-party parts, or SERP noise.

To export enriched commerce data directly to clean JSON:
```bash
google-lens search "<image-url-or-path>" --export-json deals.json
```

### 5. Real-Time Token & Cost Accounting
Every Gemini API invocation (Gemini 3.8 Flash and Nano Banana Pro) is automatically tracked using the built-in `gemini-cost-calculator`. When calling via CLI or SDK, `results.cost` returns exact token usage and financial cost in USD:
```json
"cost": {
  "model": "gemini-3.8-flash",
  "calls_count": 1,
  "tokens": { "prompt": 450, "output": 180, "total": 630 },
  "cost_usd": { "total": 0.001013 }
}
```

### 6. License Activation & Setup (Pro)
Pro features (market pricing intelligence, clean URLs, JSON export, studio packs) require an active Polar.sh license.

**Purchase a License (Browser):**
```bash
google-lens buy pro
# Or specify a plan:
google-lens buy --plan annual
```
*Opens the Polar.sh checkout page directly in your browser to choose a plan (Lifetime, Annual, or Monthly).*

**Activate in Terminal:**
```bash
google-lens pro activate "<your-polar-license-key>"
# Or run interactively:
google-lens pro activate
# Or set environment variable:
export LENS_LICENSE_KEY="<your-polar-license-key>"
```

**Check License Status:**
```bash
google-lens pro status
```

**Deactivate on this Machine:**
```bash
google-lens pro deactivate
```

### 7. Google AI Studio Key & Billing Tier (Optional)
Google Lens Scraper does **not** require any Gemini API key for regular searches or product attributes—those are deduced natively from Lens metadata with zero friction.

To synthesize 8K AI studio packshots (`--studio`) or run deep multimodal attributes, configure your key:
```bash
google-lens setup-ai --key "<your-gemini-api-key>"
# Or set environment variable:
export GEMINI_API_KEY="<your-gemini-api-key>"
```

Configure your billing tier (`unknown`, `free`, or `paid`) for exact USD cost accounting:
```bash
google-lens setup-ai --tier paid
# Or set environment variable:
export GEMINI_BILLING_TIER="paid"
```

### 8. Session Status & Google Authentication
Google Lens requires an authenticated Google session for complete visual matches and to avoid `/sorry/index` rate limits:

```bash
google-lens status
```

If unauthenticated and running in an interactive desktop environment:
```bash
google-lens login
```

For headless/cloud/CI environments, pass session state via environment variable:
```bash
export LENS_STORAGE_STATE_JSON="<base64-or-raw-json-storage-state>"
```

---

## Bundled Helper Scripts

For programmatic workflows and batch operations, use the bundled scripts located in `scripts/`. These scripts include [PEP 723](https://peps.python.org/pep-0723/) inline dependency metadata.

### Single Image Search & Filtering (`scripts/search_image.py`)
Search an image with built-in filtering by price, result count, or mode:

```bash
# Basic search with JSON output
python3 scripts/search_image.py "https://example.com/photo.jpg" --json

# Filter visual matches (e.g. max 5 results)
python3 scripts/search_image.py "path/to/image.png" --max-results 5 --json

# Fast OCR extraction
python3 scripts/search_image.py "path/to/receipt.jpg" --ocr-only --json
```

### Batch Image Processing (`scripts/batch_search.py`)
Process a directory of images or a list of URLs asynchronously:

```bash
# Process all images in a directory
python3 scripts/batch_search.py --dir ./images/ --output ./batch_results.json

# Process list of URLs from file
python3 scripts/batch_search.py --urls-file ./image_urls.txt --output ./batch_results.json --concurrency 3
```

---

## Interpreting Output

When `--json-output` is used, the JSON payload follows this structure:

```json
{
  "query": "https://example.com/item.jpg",
  "ocr_text": "Detected text from the image...",
  "knowledge_graph": {
    "title": "Identified Object / Entity Name",
    "subtitle": "Classification (e.g. Footwear / Plant)",
    "description": "Brief encyclopedic description",
    "website": "https://..."
  },
  "commerce": {
    "summary": {
      "target_product": "Nike Free RN Flyknit 2017",
      "min_price": 120.0,
      "max_price": 120.0,
      "avg_price": 120.0,
      "currency": "USD",
      "total_matches": 69,
      "total_priced_matches": 1
    },
    "items": [
      {
        "title": "Nike Free RN Flyknit 2017",
        "direct_url": "https://www.goat.com/sneakers/free-rn-flyknit-2017-880843-006",
        "match_score": 97,
        "relevance": "exact_match",
        "relevance_reason": "Direct marketplace listing for identical silhouette.",
        "page_type": "product",
        "price": { "raw": "120.00 USD", "amount": 120.0, "currency": "USD" },
        "merchant_name": "GOAT"
      }
    ]
  },
  "visual_matches": [
    {
      "title": "Product Title",
      "link": "https://store.com/item",
      "source": "Store Name",
      "price": "$99.00",
      "thumbnail": "https://..."
    }
  ],
  "detected_objects": [
    {
      "id": "item_1",
      "bounding_box": {
        "center_x": 0.5,
        "center_y": 0.5,
        "width": 0.3,
        "height": 0.4
      }
    }
  ]
}
```

---

## Troubleshooting & Best Practices

1. **Bot Clearance (HTTP 429 / CAPTCHA)**: If visual match requests are rate-limited, switch to `--ocr-only` (guaranteed zero CAPTCHAs) or authenticate via `google-lens login` or `LENS_STORAGE_STATE_JSON`.
2. **Local Images**: Local file paths (`.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`, `.gif`) are automatically uploaded to Google's fast-upload endpoint.
3. **Headless Execution**: Searches run headless by default. In debugging environments, pass `--no-headless` to inspect the browser.

For complete CLI flags, configuration parameters, and detailed JSON schemas, see [references/REFERENCE.md](references/REFERENCE.md).
