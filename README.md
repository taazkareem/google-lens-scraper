<div align="center">
  <img src="https://raw.githubusercontent.com/taazkareem/google-lens-scraper/main/assets/banner.jpg" alt="Google Lens Scraper — Unofficial Python API, Reverse Image Search & Fast-Path OCR" width="100%" style="border-radius: 8px;">
</div>

<br/>

# Google Lens Scraper (`google-lens-scraper`)

[![PyPI version](https://img.shields.io/pypi/v/google-lens-scraper?color=blue)](https://pypi.org/project/google-lens-scraper/)
[![Python versions](https://img.shields.io/pypi/pyversions/google-lens-scraper?color=blue)](https://pypi.org/project/google-lens-scraper/)
[![GitHub Stars](https://img.shields.io/github/stars/taazkareem/google-lens-scraper?style=flat&color=yellow)](https://github.com/taazkareem/google-lens-scraper/stargazers)
[![License: Proprietary / Dual](https://img.shields.io/badge/License-Dual%20MIT%20%2F%20Pro-blue.svg)](LICENSE)
[![Polar Pro](https://img.shields.io/badge/Polar.sh-Pro%20Available-0069ff.svg)](https://buy.polar.sh/polar_cl_LvZYm1TaDHiQof4M4DyiLjMXVnV8y7DtJkcCK21Xpc8)
[![Agent Skill: google-lens](https://img.shields.io/badge/Agent%20Skill-google--lens-8A2BE2.svg)](https://agentskills.io)

**Google Lens Scraper** is a high-performance Python package and CLI for reverse-engineered **Google Lens visual search**, **reverse image lookup**, and **OCR text extraction** using **Patchright** stealth browser automation and native **Chromium Protobuf** protocols. Fast, developer-friendly, and self-hosted alternative to expensive cloud proxy APIs like SerpApi and TinEye. No API keys required. Optional Pro Tier available with complete features.


---

## Table of Contents

- [Why Google Lens Scraper? (Comparison)](#why-google-lens-scraper)
- [Common Use Cases](#common-use-cases)
- [Core Features](#features)
- [Installation](#installation)
- [Quick Start](#-quick-start)
  - [1. Command Line (CLI)](#1-command-line-cli)
  - [2. AI Coding Agents](#2-ai-coding-agent-cursor-claude-code-copilot-codex-gemini-cli)
- [Google Lens Pro (Commercial Intelligence Suite)](#-google-lens-pro--resale--visual-intelligence-suite)
- [Python SDK Integration](#-python-sdk--developer-integration)
  - [Visual Search (Sync)](#1-synchronous-search-visual-matches--ocr)
  - [Fast-Path OCR (Zero Browser, Sub-Second)](#2-fast-path-ocr--object-detection-only-sub-second-no-browser)
  - [Asynchronous Search (AsyncIO)](#3-asynchronous-search)
- [Agent Skill Integration](#agent-skill-google-lens)
- [Authentication & Headless Deployments](#authentication-one-time-setup)
- [CLI Reference & Commands](#cli-usage)
- [Configuration Options](#configuration-options)
- [Data Models](#data-models)
- [Frequently Asked Questions (FAQ)](#frequently-asked-questions-faq)
- [License & Terms](#license--commercial-terms)

---

## Features

- **Tri-Modal Search Inputs**: Query using public image URLs, local image files (`.png`, `.jpg`, `.webp`), raw image bytes, or existing Google Lens search result URLs (`udm=26` / `udm=44`).
- **All-By-Default Execution**: One command (`google-lens search <image>`) retrieves visual matches, normalizes prices, unwraps canonical links, and extracts deep attributes.
- **Dual-Engine Architecture**:
  - **Fast-Path Protobuf Engine**: Uses Chromium's native internal endpoint (`v1/crupload`) for sub-second, zero-browser image uploads, session token generation (`gsessionid` / `lsessionid`), and full-text OCR.
  - **Stealth Browser Engine**: Powered by Patchright (undetected Chromium driver) for complete visual matches, thumbnails, publisher URLs, prices, and Knowledge Graph entities.
- **Category-Agnostic AI Match Evaluation**: Bundled candidate evaluations classify matches into `exact_match`, `similar`, `reference`, or `unrelated` with human-readable rationale (`relevance_reason`) and automatically identify the target product (`target_product`) across luxury goods, electronics, fashion, and collectibles.
- **Zero-Friction Agent Fallback**: Works natively without an API key! If `GEMINI_API_KEY` is not present, the bundled Agent Skill directs host LLMs to analyze attributes in-context.
- **Nano Banana Pro 8K Studio Generation**: Pass `--studio` to synthesize isolated commercial catalog packshots to disk.
- **Permanent Session Authentication**:
  - `google-lens login` command captures Google account credentials once to run 100% headless visual searches indefinitely.
  - Automatic session loading from `~/.config/google-lens-scraper/session.json`.
  - Production & CI/CD support via `LENS_STORAGE_STATE_JSON` or `LENS_COOKIES` environment variables.
- **Anti-Bot Defenses**:
  - Coherent Client Hints (`sec-ch-ua`) matching internal browser fingerprints.
  - Injected session cookies (`SOCS`, `CONSENT`, `SID`, `HSID`).
  - Persistent browser profiles (`user_data_dir`) and Chrome DevTools Protocol (`cdp_url`).
  - HTTP & SOCKS5 proxy support.
- **Dual Synchronous & Asynchronous APIs**: `LensScraper` and `AsyncLensScraper` with native concurrent destination enrichment (`enrich_async`).
- **Command-Line Interface**: `google-lens` CLI for quick searches, OCR, and session management.
- **Agent Skill Integration**: Built-in open-standard Agent Skill conforming to [agentskills.io](https://agentskills.io) for VS Code Copilot, Claude Code, Cursor, Codex, and Gemini CLI.

---

## Common Use Cases

- **🔍 Reverse Image Search**: Find original image sources, higher-resolution copies, and related web pages from any image URL or local image path.
- **🛍️ E-Commerce & Product Matching**: Discover where products, sneakers, clothing, or furniture are sold online and compare prices across merchants.
- **⚡ Sub-Second AI OCR**: Extract dense text, receipts, handwritten notes, and serial numbers with Google's state-of-the-art vision models in milliseconds—without launching a browser.
- **🏛️ Knowledge Graph Recognition**: Automatically identify landmarks, plants, dog breeds, artwork, and historical figures from photos.
- **🤖 AI Coding Agent Vision Tool**: Equip your AI assistant (Claude Code, Cursor, Copilot, Codex, Gemini CLI) to browse the visual web natively.

---

## Installation

```bash
pip install google-lens-scraper
```
*(Provides the `google-lens` CLI command)*

Install the stealth Chromium browser binary:
```bash
patchright install chromium
```

---

## 🚀 Quick Start

Get results in seconds via the CLI or your AI coding assistant:

### 1. Command Line (CLI)

```bash
# Authenticate once with Google (opens browser to capture session)
google-lens login

# Search any image URL or local photo (retrieves matches, prices, Knowledge Graph)
google-lens "path/to/sneakers.jpg"

# Or extract text with sub-second OCR (fast-path Protobuf, zero browser required):
google-lens "receipt.png" --ocr-only
```

### 2. AI Coding Agent (Cursor, Claude Code, Copilot, Codex, Gemini CLI)

```bash
# Install the open Agent Skill directly into your workspace
google-lens install-skill
```

Prompt your AI agent in plain English:
> *"Find where to buy the jacket in this image: https://example.com/jacket.jpg"*  
> *"Find high-quality visual matches and the original source for wallpaper.png"*

---

<div align="center">

<h2 align="center">💎 Google Lens Pro — Resale & Visual Intelligence Suite</h2>

Unlock automated **E-Commerce & Resale Arbitrage Intelligence** (`--enrich`), **Deep Destination Extraction** (Schema.org LD-JSON, Next.js hydration, OpenGraph), **Page Intent Classification**, **Stock & Availability Detection**, **Clean Canonical URLs**, **Multi-Currency Price Normalization**, **Best-Deal Detection**, and **Direct JSON Pipelines**:

<br>

| [**Monthly**](https://buy.polar.sh/polar_cl_nVrJAfC1HXmCMV1T2l1KwcbiiM0FavN8DccGo0K1E0Q?utm_source=github&utm_medium=readme) $19/mo | [**Annual**](https://buy.polar.sh/polar_cl_CWQxn1LtnLUbf5alOQMUgzTIQRQUrXjk6vXXQ0d5wBx?utm_source=github&utm_medium=readme) $99/yr | [**Lifetime**](https://buy.polar.sh/polar_cl_LvZYm1TaDHiQof4M4DyiLjMXVnV8y7DtJkcCK21Xpc8?utm_source=github&utm_medium=readme) $99 (Launch Special) |
| :--- | :--- | :--- |
| • Full pricing & currency normalization<br>• Canonical URL unwrapping<br>• 3 device activations<br>• Cancel anytime | • **Save 55%** ($8.25/mo)<br>• Best Deal lowest-price detector<br>• 3 device activations<br>• Priority updates | • **Best Value — One payment**<br>• Unlocked Forever<br>• 3 device activations<br>• Deep destination enrichment<br>• Direct JSON data pipelines |

<br>

<p align="center">
  <img src="https://raw.githubusercontent.com/taazkareem/google-lens-scraper/main/assets/images/line.svg" width="150" alt="divider line" style="vertical-align: middle;">&nbsp;&nbsp;<a href="https://buy.polar.sh/polar_cl_LvZYm1TaDHiQof4M4DyiLjMXVnV8y7DtJkcCK21Xpc8?utm_source=github&utm_medium=readme"><img src="https://img.shields.io/badge/PURCHASE%20PRO%20LICENSE-0069ff?style=for-the-badge&logo=polar&logoColor=white" alt="Purchase License" style="vertical-align: middle;"></a>&nbsp;&nbsp;<img src="https://raw.githubusercontent.com/taazkareem/google-lens-scraper/main/assets/images/line.svg" width="150" alt="divider line" style="vertical-align: middle;">
</p>

<br>

</div>

### What Pro Adds:
1. **🌐 Deep Destination Page Enrichment (`--enrich`)**: Concurrently fetches destination pages using Scrapling's high-performance HTTP engine to extract rich metadata that never appears in search snippets.
2. **📦 Schema.org & Next.js Hydration Extraction**: Parses LD-JSON (`Product`, `Offer`), Next.js hydration payload (`__NEXT_DATA__`), and OpenGraph tags directly from merchant product pages.
3. **🎯 Page Intent Classification (`page_type`)**: Automatically categorizes destination URLs into `product`, `article`, `social` (Instagram, TikTok, Pinterest), `portfolio`, `marketplace`, or `uncategorized` so you can instantly filter out non-shoppable links.
4. **📊 Stock & Availability Detection (`stock_status`)**: Identifies real-time merchant stock levels (`in_stock`, `out_of_stock`, `preorder`) directly from product feeds.
5. **🏷️ Item Condition & SKU Extraction (`condition`, `sku`)**: Captures condition (`new`, `used`, `refurbished`) and product identifiers (GTIN, UPC, SKU) for resale pricing and catalog matching.
6. **🔗 Canonical URL Unwrapping**: Decodes opaque `google.com/url?q=...` redirects into direct, clean merchant product links, stripping UTM parameters, ad click-trackers, and Chrome text fragments.
7. **💰 Normalized Pricing & Best Deals**: Auto-extracts numeric prices and currencies (USD, EUR, GBP, INR, etc.), computing market average/range and highlighting the lowest-priced verified seller.
8. **🏪 Merchant Categorization**: Labels sellers as Official Brand stores (e.g. Nike, Apple), Major Marketplaces (Amazon, eBay, Walmart), or Resellers (StockX, GOAT, Chrono24).
9. **📁 Clean JSON-First Data Pipelines**: Direct `--export-json` (or `--export`) flag for developer-grade hierarchical data without sparse, inconsistent CSV columns or `null` noise.
10. **⚡ Multi-Device Activations**: Authorize up to 3 machines simultaneously via CLI (`google-lens pro activate <key>`) or purchase directly (`google-lens buy pro`) with self-service license management in the Polar customer portal.
11. **🎯 Category-Agnostic Semantic Match Evaluation (`relevance`)**: Separates exact product matches from accessories, lookalikes, and unrelated SERP noise (`exact_match`, `similar`, `reference`, `unrelated`) with transparent, human-readable rationale (`relevance_reason`).
12. **🏷️ Target Product Identification (`target_product`)**: Automatically detects the canonical item name and silhouette from visual cues and metadata, anchoring all price comparison and match score analytics.

---

## Why Google Lens Scraper?

| Feature | `google-lens-scraper` (Free / MIT) | `google-lens-scraper` (Pro) | SerpApi / Proxy APIs | Google Cloud Vision API |
| :--- | :--- | :--- | :--- | :--- |
| **Pricing** | **100% Free & Open Source** | **$19/mo, $99/yr, or $99 Lifetime** | $75 – $250+/month | $1.50 per 1,000 requests |
| **Search Volume** | **Unlimited Local Searches** | **Unlimited Local Searches** | Strictly Metered (5k/mo) | Metered per API call |
| **Fast-Path OCR & Bounding Boxes** | ✅ Sub-second (Zero browser) | ✅ Sub-second (Zero browser) | ❌ High API latency | ✅ Paid per image |
| **Visual Match Results** | ✅ Yes (Full Google Web Matches) | ✅ Yes (Full Google Web Matches) | ✅ Yes | ❌ Web detection only |
| **Direct Canonical URLs** | ⚠️ Google redirect links | ✅ Clean direct merchant links | ❌ Often wrapped | ❌ N/A |
| **Deep Destination Crawling (`--enrich`)** | 🔒 1-Item Teaser Preview | ✅ Concurrent Scrapling HTTP Engine | ❌ None (SERP only) | ❌ None |
| **Schema.org & Next.js Hydration** | 🔒 1-Item Teaser Preview | ✅ Deep LD-JSON & `__NEXT_DATA__` | ❌ None | ❌ None |
| **Page Intent Classification** | 🔒 1-Item Teaser Preview | ✅ Product vs Article vs Social | ❌ None | ❌ None |
| **Stock & Availability Detection** | 🔒 1-Item Teaser Preview | ✅ In Stock, Out of Stock, Preorder | ❌ None | ❌ None |
| **Condition & SKU / GTIN Extraction** | 🔒 1-Item Teaser Preview | ✅ New / Used / Refurbished + GTIN | ❌ None | ❌ None |
| **Title Cleaning & Normalization** | Raw search snippet | ✅ Clean titles (cures "Read more") | ❌ Raw snippet only | ❌ None |
| **Price Comparison & Best Deal** | 🔒 1-Item Teaser Preview | ✅ Full Min/Max/Avg + Best Deal | ❌ Raw unparsed strings | ❌ None |
| **Merchant Categorization** | 🔒 1-Item Teaser Preview | ✅ Brand vs Marketplace vs Reseller | ❌ No | ❌ No |
| **AI Semantic Match Evaluation** | 🔒 1-Item Teaser Preview | ✅ Category-Agnostic Gemini 3.8 Flash (`relevance`) | ❌ None (SERP only) | ❌ None |
| **JSON Data Pipeline Export** | 🔒 Teaser Only | ✅ Full `--export-json` | ⚠️ Extra export fees | ❌ Custom code required |
| **Product Attribute Extraction** | ✅ Native Zero-Key Deduction | ✅ Native + Gemini 3.8 Flash | ❌ None | ❌ None |
| **8K Studio Packshots (`--studio`)** | ✅ Nano Banana Pro (w/ AI key) | ✅ Nano Banana Pro (w/ API key) | ❌ None | ❌ None |
| **AI Agent Skill (`SKILL.md`)** | ✅ Built-in ([agentskills.io](https://agentskills.io)) | ✅ Built-in ([agentskills.io](https://agentskills.io)) | ❌ Custom code required | ❌ Custom code required |


---

## Agent Skill (`google-lens`)

`google-lens-scraper` includes a pre-packaged, specification-compliant [Agent Skill](https://agentskills.io/home) that gives AI coding agents (VS Code GitHub Copilot, Claude Code, Cursor, Codex, Gemini CLI, Hermes, etc.) native visual search and OCR tools.

### Installing the Skill

To install the skill into your current workspace:

```bash
google-lens install-skill
```

This installs the skill to `.agents/skills/google-lens/`.

#### Additional Installation Options:
- **Global User Install**: `google-lens install-skill --global` (installs to `~/.agents/skills/google-lens/`)
- **Claude Code**: `google-lens install-skill --claude` (installs to `.claude/skills/google-lens/`, or combine with `--global`)
- **Custom Directory**: `google-lens install-skill --dest ./my-skills/`
- **Force Overwrite**: `google-lens install-skill --force`

### Example Prompts for Agents

Once installed, your AI agent automatically activates the skill when you ask visual tasks:
- *"Find where to buy the jacket in this image: https://example.com/jacket.jpg"*
- *"Find high-quality visual matches and the original source for wallpaper.png"*
- *"Extract all text from receipt.png using Google Lens OCR"*
- *"Identify what landmark or building is shown in photo.jpg"*
- *"What is the estimated price of the watch in this picture?"*

---

## Authentication (One-Time Setup)

Google Lens requires session trust to display full visual matches on modern search layouts. You can authenticate once and run all subsequent searches headlessly:

### CLI Login
```bash
# Authenticate and save session locally
google-lens login

# Or authenticate and automatically write credentials to a local .env file
google-lens login --env
```
A browser window will open. Sign into your Google account (or dismiss any prompts) and press **[Enter]** in your terminal. Your session will be saved securely to `~/.config/google-lens-scraper/session.json` (and written to `.env` if `--env` is passed).

Check session status anytime:
```bash
google-lens status
```

To log out:
```bash
google-lens logout
```

### Production / Docker / CI Deployments
In containerized, cloud, or headless CI environments where an interactive browser cannot be opened, provide the session state via environment variables or a `.env` file:

1. **Export your authenticated session from your local machine**:
   ```bash
   # Automatically create or update your local .env file
   google-lens export-session --env

   # Or print the base64 string to copy into a cloud secret manager
   google-lens export-session --base64
   ```
   *What is this?* This dumps your authenticated session (Playwright browser storage state containing your Google session cookies) as a single-line base64 string. Using base64 prevents quote-escaping and multiline syntax issues when pasting into `.env` files, Docker `-e` flags, Kubernetes secrets, or cloud secret managers.

2. **Set the environment variable in your production runtime or `.env` file**:
   ```bash
   # Base64-encoded or raw JSON storage state (ideal for secret managers / Docker)
   export LENS_STORAGE_STATE_JSON="eyJjb29raWVzIjog..."

   # Or point to a mounted secret file on disk
   export LENS_STORAGE_STATE_PATH="/secrets/google-lens-session.json"

   # Or provide cookie headers directly
   export LENS_COOKIES="SID=...; SOCS=..."
   ```

> **Note:** If a `.env` file is present in the working directory, `google-lens-scraper` will automatically load any `LENS_*` variables defined in it.

---

## 🐍 Python SDK & Developer Integration

### 1. Synchronous Search (Visual Matches + OCR)

```python
from google_lens_scraper import LensScraper

# Initialize scraper (automatically uses saved session if available)
scraper = LensScraper(headless=True)

# Search local file or image URL
result = scraper.search("path/to/product.jpg")
# result = scraper.search("https://example.com/sneakers.jpg")

# Access detected objects & OCR
print("Identified:", result.knowledge_graph.title if result.knowledge_graph else "N/A")
print("OCR Text:", result.ocr_text)

# Access product attributes (deduced natively without API keys)
if result.analysis and result.analysis.attributes:
    attrs = result.analysis.attributes
    print(f"Brand: {attrs.brand} | Model: {attrs.model_or_name} | Category: {attrs.category}")

# Access Pro commerce intelligence (best deal & clean URLs)
if result.commerce and result.commerce.best_deal:
    deal = result.commerce.best_deal
    print(
        f"Best Deal: {deal.price.amount} {deal.price.currency} at {deal.merchant_name} -> {deal.direct_url}"
    )

# Iterate through visual matches
print(f"\nFound {len(result.visual_matches)} visual matches:")
for match in result.visual_matches:
    print(f"- [{match.source}] {match.title}")
    print(f"  URL: {match.link}")
    if match.price:
        print(f"  Price: {match.price}")
    print(f"  Thumbnail: {match.thumbnail}\n")
```

### 2. Fast-Path OCR & Object Detection Only (Sub-Second, No Browser)

If you only need OCR text and bounding boxes without launching a browser:

```python
from google_lens_scraper import LensScraper

scraper = LensScraper()
result = scraper.detect("path/to/receipt.jpg")

print("OCR Text:", result.ocr_text)
for obj in result.detected_objects:
    print("Object:", obj.id, obj.bounding_box)
```

### 3. Asynchronous Search (AsyncIO + Concurrent Pro Enrichment)

```python
import asyncio
from google_lens_scraper import AsyncLensScraper


async def main():
    scraper = AsyncLensScraper(headless=True)
    result = await scraper.search("https://example.com/watch.jpg")

    # Visual match items
    for match in result.visual_matches:
        print(f"[{match.source}] {match.title} -> {match.link}")

    # Pro commerce intelligence (async destination enrichment & relevance)
    if result.commerce:
        print(f"\nTarget Product: {result.commerce.summary.target_product}")
        for match in result.commerce.items:
            rel = f"[{match.relevance.value}]" if match.relevance else ""
            print(
                f"- {match.title} | {match.price.raw if match.price else 'N/A'} {rel} -> {match.direct_url}"
            )


asyncio.run(main())
```

---

## Configuration Options

Configure `LensConfig` for custom proxies, timeouts, or profiles:

```python
from google_lens_scraper import LensConfig, LensScraper

config = LensConfig(
    headless=True,
    timeout=30.0,
    # Residential proxy
    proxy="http://user:pass@proxy.example.com:8080",
    # Custom cookies
    cookies="SID=...; HSID=...",
    # Custom persistent Chrome user data directory
    user_data_dir="~/.config/google-chrome/Default",
    # Or connect to an existing Chrome browser via CDP
    cdp_url="http://localhost:9222",
    # Language and Region
    language="en",
    region="US",
)

scraper = LensScraper(config=config)
```

---

## CLI Usage

The package includes the `google-lens` command-line utility:

```bash
# -------------------------------------------------------------
# 1. Google Session Authentication
# -------------------------------------------------------------
# Authenticate interactively once to bypass bot detection
google-lens login

# Check authentication status
google-lens status

# Export session state for headless servers / CI (.env or base64)
google-lens export-session --env
google-lens export-session --base64

# Log out / clear saved credentials
google-lens logout

# -------------------------------------------------------------
# 2. Visual Search & Intelligence (Core Search & OCR)
# -------------------------------------------------------------
# Search an image (runs visual search, price normalization & native attribute extraction)
google-lens image.jpg

# Search public image URL
google-lens "https://example.com/item.jpg"

# Sub-second OCR and object detection only (zero browser overhead)
google-lens document.png --ocr-only

# Output raw JSON to stdout (great for jq / piping)
google-lens image.jpg --json-output | jq .visual_matches

# Use a proxy
google-lens image.jpg --proxy "http://user:pass@proxy:8080"

# -------------------------------------------------------------
# 3. Pro Licensing & Plans (Optional Commercial Tier)
# -------------------------------------------------------------
# Purchase Pro license (opens Polar.sh checkout in browser)
google-lens buy pro                    # Opens Lifetime checkout (default)
google-lens buy --plan annual          # Or: --plan monthly

# Activate license in terminal (direct key or interactive prompt)
google-lens pro activate "<your-polar-license-key>"
google-lens pro activate               # Interactive prompt

# Check license status & authorized devices
google-lens pro status

# Deactivate license on this machine
google-lens pro deactivate

# Export enriched product & arbitrage deals to clean JSON (Pro feature)
google-lens image.jpg --export-json deals.json

# -------------------------------------------------------------
# 4. AI Studio & Gemini Configuration
# -------------------------------------------------------------
# Configure Google AI Studio key (optional, for --studio packshots & deep attributes)
google-lens setup-ai --key "<your-gemini-api-key>"

# Configure billing tier for exact cost accounting (unknown, free, or paid)
google-lens setup-ai --tier paid       # Or: --tier free / --tier unknown

# Check AI Studio key and tier status
google-lens setup-ai --status

# Generate 8K commercial studio packshot via Nano Banana Pro
google-lens image.jpg --studio --studio-output ./packshot.png
```

> **Tip:** In `zsh` and other POSIX shells, always enclose URLs containing query parameters (`&`, `?`) in quotation marks (e.g. `google-lens "https://..."`) to prevent shell parse errors.

---

## Data Models

Results are encapsulated in the `LensSearchResult` Pydantic model:

```python
class LensSearchResult(BaseModel):
    query_url: Optional[str]  # Executed Google Lens URL
    search_session_id: Optional[str]  # Google gsessionid token
    server_session_id: Optional[str]  # Google lsessionid token
    ocr_text: Optional[str]  # Full OCR text extracted
    detected_objects: List[DetectedObject]  # Detected bounding boxes & labels
    visual_matches: List[VisualMatch]  # Web shopping and visual match items
    knowledge_graph: Optional[KnowledgeGraph]  # Encyclopedic Knowledge Graph card
    commerce: Optional[CommerceIntelligence]  # Pro: Clean URLs, normalized prices, best deal
    analysis: Optional[VisualAnalysis]  # Native & multimodal product attributes
    studio_asset: Optional[GeneratedStudioAsset]  # Synthesized 8K commercial packshot
    cost: Optional[Dict[str, Any]]  # Real-time token usage and USD financial cost

    def to_dict(self) -> dict: ...
    def to_json(self) -> str: ...
```

### Core Sub-Models:
- **`VisualMatch`**: `title`, `link`, `thumbnail`, `source`, `price`.
- **`CommerceIntelligence` (Pro)**: `summary` (`target_product`, min/max/average price across verified listings, currency, `best_deal`), `items` (all matches classified by `page_type`, `match_score`, and semantic `relevance`), `products` (filtered commercial listings), `is_preview`.
- **`EnrichedCommerceMatch` (Pro)**: `title`, `direct_url` (unwrapped clean canonical URL), `price` (`raw`, `amount`, `currency`), `merchant_name`, `merchant_category`, `thumbnail`, `match_score` (0-100% token overlap), `relevance` (`exact_match`, `similar`, `reference`, `unrelated`), `relevance_reason`, `page_type`, `brand`, `sku`, `condition`, `stock_status`, `in_stock`.
- **`VisualAnalysis`**: `summary`, `attributes` (`brand`, `model_or_name`, `category`, `color`, `materials`, `condition_assessment`, `authenticity_markers`, `confidence_score`), `resale_recommendation`, `tags`.
- **`GeneratedStudioAsset`**: `image_path` (saved 8K file), `prompt_used`, `aspect_ratio`, `model`.
- **`Cost Telemetry`**: `tokens.total`, `tokens.prompt`, `tokens.output`, `cost_usd.total`, `billing_tier`.

---

## Frequently Asked Questions (FAQ)

<details>
<summary><b>Does Google offer an official Google Lens API?</b></summary>

No. Google does not provide a public developer API for Google Lens. Most developers rely on expensive third-party proxy services like SerpApi. `google-lens-scraper` reverse-engineers Chromium's native internal endpoint (`v1/crupload`) and combines it with Patchright stealth browser automation to give you direct, self-hosted access without recurring per-request API fees.
</details>

<details>
<summary><b>Can I use this as a free alternative to SerpApi's Google Lens API?</b></summary>

Yes. `google-lens-scraper` was built specifically to replace costly third-party scraping APIs like SerpApi (which charges $75–$250+/month for metered searches). The open-source MIT core allows unlimited local visual searches, reverse image lookups, and OCR text extraction directly from your own hardware or servers at zero API cost.
</details>

<details>
<summary><b>Do I need a Gemini API key or Google Cloud billing to use this?</b></summary>

No. The core reverse image search, OCR text extraction, Knowledge Graph detection, and zero-key visual attribute deduction work 100% locally without any API keys. A Gemini API key is strictly optional—only needed if you want to use the `--studio` command to generate AI-synthesized 8K commercial product packshots via Nano Banana Pro.
</details>

<details>
<summary><b>How does the Fast-Path Protobuf mode work without a browser?</b></summary>

When you use `scraper.detect()` or the `--ocr-only` CLI flag, the library communicates directly with Google's binary Protobuf upload endpoint (`https://lensfrontend-pa.googleapis.com/v1/crupload`). It uploads the image bytes, receives the parsed Protobuf response, and extracts OCR text and bounding boxes in sub-second time without launching Chromium.
</details>

<details>
<summary><b>Can I use this for e-commerce price comparison and resale arbitrage?</b></summary>

Yes. Google Lens searches return structured visual matches across major e-commerce platforms (Amazon, eBay, Walmart, StockX, Nike, etc.). With the Pro suite enabled (`--enrich`), the scraper automatically unwraps Google redirect links into canonical merchant URLs, normalizes prices across currencies (USD, EUR, GBP, etc.), identifies the best deal, and exports structured data to JSON pipelines (`--export-json`).
</details>

<details>
<summary><b>How do I run Google Lens in Docker, Kubernetes, or headless CI?</b></summary>

Authenticate once on your local machine using `google-lens login`. Then export your session string via `google-lens export-session --base64` and set it as the `LENS_STORAGE_STATE_JSON` environment variable in your production container or `.env` file. Google will treat the headless browser as a trusted, authenticated session.
</details>

<details>
<summary><b>How do I avoid Google bot detection and HTTP 429 rate limits?</b></summary>

The package includes built-in anti-detection defenses: coherent Client Hints (`sec-ch-ua`), authenticated session cookies, and Patchright undetected browser drivers. For high-throughput production scraping, configure residential or mobile proxies using `LensConfig(proxy="http://user:pass@proxy:8080")` or the `--proxy` CLI flag.
</details>

<details>
<summary><b>How do I equip Claude Code, Cursor, or AI coding agents with Google Lens vision?</b></summary>

Run `google-lens install-skill` in your terminal. This installs the specification-compliant Agent Skill (`.agents/skills/google-lens/`) conforming to [agentskills.io](https://agentskills.io). Your AI coding agent (Cursor, Claude Code, GitHub Copilot, Codex, Gemini CLI) will then automatically call `google-lens` whenever you ask it to inspect images, identify products, or extract text in plain English.
</details>

---

## License & Commercial Terms
 
- **Community Core & Agent Skill**: Open source under the [MIT License](LICENSE). Free for unlimited local visual search, reverse image lookups, sub-second Protobuf OCR, Knowledge Graph card extraction, and native zero-key attribute deductions.
- **Pro Commercial Intelligence Suite** (`license.py`, `commerce.py`): Proprietary, see [LICENSE](LICENSE). Requires an active license key from [Polar.sh](https://buy.polar.sh/polar_cl_LvZYm1TaDHiQof4M4DyiLjMXVnV8y7DtJkcCK21Xpc8?utm_source=github&utm_medium=readme) for concurrent destination page enrichment, Schema.org LD-JSON and Next.js hydration extraction, page intent classification, stock status detection, direct canonical URL unwrapping, multi-currency price arbitrage, best-deal ranking, and automated JSON export pipelines.

