# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-09-06

### Added
- **Clean Rebranding to `google-lens-pro`**:
  - Rebranded distribution to `google-lens-pro` on PyPI to reflect its evolution into a full visual discovery, multimodal AI, and multi-marketplace commercial intelligence suite.
  - Clean transition to `google_lens_pro` namespace and published CLI aliases `lens`, `google-lens`, and `google-lens-pro`.
  - Updated all documentation, license files, CI workflows, and assets (including a brand new AI-generated `assets/banner.jpg`).
- **Direct Store Product URL Crawler (`DirectStoreResolver`)**:
  - Automatically crawls merchant search results concurrently using Scrapling's `AsyncFetcher` to resolve exact direct product SKU URLs (e.g. `poshmark.com/listing/...`, `goat.com/sneakers/...`, `flightclub.com/...`) instead of generic site search URLs.
  - Concurrency limited via `asyncio.Semaphore(8)` with URL deduplication cache and 4-second timeout.
  - Real-time progress updates stream live to the terminal spinner (`Resolving direct product links (X/Y)...`).
- **Free vs. Pro Tier Clarification & Paywall Precision**:
  - Clarified that Google Lens visual reverse image search, OCR text extraction, and Gemini 3.8 Flash multimodal vision are completely free / BYOK (`GEMINI_API_KEY`).
  - Pro license unlocks unlimited multi-store pricing fusion (50+ listings from StockX, GOAT, Flight Club, eBay, Walmart), direct product SKU URL crawling, market valuation analytics, and bulk dataset exports.
- **Modular Domain Architecture**:
  - Decomposed monolithic modules into domain-driven subpackages:
    - `core/`: Centralized authentication (`auth.py`), stealth browser contexts (`browser.py`), configuration (`config.py`), concurrent HTTP fetcher (`fetcher.py`), and licensing (`license.py`).
    - `models/`: Clean typed Pydantic models for common primitives (`common.py`), Google Lens (`lens.py`), Google Shopping (`shopping.py`), commerce intelligence (`commerce.py`), and unified results (`result.py`).
    - `commerce/`: Modularized destination unwrapping (`unwrapper.py`), price normalization (`normalizer.py`), seller classification (`classifier.py`), LD-JSON/Next.js metadata extraction (`metadata.py`), and market analytics aggregation (`aggregator.py`).
    - `engines/shopping/`: Dedicated Google Shopping engine (`engine.py`) and HTML parser (`parser.py`) for scraping SERPs and comparative multi-seller product tables.
    - `pipeline/`: Unified Fusion Pipeline orchestrator (`orchestrator.py`) combining visual discovery and live shopping offers.
- **Google Shopping Engine (`ShoppingEngine`)**:
  - Sub-second retrieval of Google Shopping offers via Scrapling HTTP with automatic Patchright stealth browser fallback.
  - Extracts verified merchant pricing, direct store URLs, shipping details, star ratings, review counts, stock status, and item condition.
  - Supports `--country` (`gl=`) and `--currency` (`hl=`) parameters for localized international e-commerce intelligence.
  - Supports `--deep` scraping of comparative product tables (`/shopping/product/...`) across all participating merchants.
- **Unified Fusion Pipeline (`FusionOrchestrator`)**:
  - Unifies Google Lens visual matches, Gemini multimodal identification, real-time Google Shopping offers, and deep destination metadata.
  - Cross-source merchant deduplication, unified market pricing analytics (min/max/average prices), and verified best deal highlight.
  - Exposed via `GoogleLens.fuse()` and `AsyncGoogleLens.fuse()`, as well as `google_lens_scraper._pro.fuse()`.
- **Smart CLI Dispatch & `lens` Binary**:
  - Added short CLI binary alias `lens` in `[project.scripts]`.
  - Smart root CLI dispatch: `lens <input>` automatically routes text queries/UPCs to Google Shopping (`shop`) and image paths/URLs/bytes to Google Lens visual search (`search`).
  - Dedicated `lens shop` subcommand with `--country`, `--currency`, `--deep`, `--max-results`, `--export-json`, and `--export-csv` options.
- **Unified Developer SDK (`GoogleLens` & `AsyncGoogleLens`)**:
  - Primary `GoogleLens` client export with `search()`, `search_shopping()`, `fuse()`, `detect()`, and `ocr()` APIs.
- **Live Terminal Progress Indicator (`rich.status`)**: Added real-time progress feedback on `stderr` during interactive CLI searches (`google-lens search`). Features an animated spinner displaying dynamic pipeline stages (Lens navigation, merchant destination metadata scraping, price intelligence extraction, and multimodal AI analysis) that cleans up automatically on completion.
- **Decoupled `on_progress` SDK Hook**: Added `on_progress: ProgressCallback | None` across `LensScraper.search()`, `LensScraper.detect()`, `AsyncLensScraper.search()`, and `CommerceEnricher.process()`, allowing library consumers to subscribe to granular pipeline stage events without coupling the scraping engine to console output.
- **Strict Stderr Isolation**: Ensured all progress telemetry is routed to `sys.stderr` and suppressed automatically when `--json-output` is requested or stdout/stderr is redirected, ensuring zero corruption for pipes (`| jq`) and automation workflows.

### Changed
- **Consolidated CLI Terminal Dashboard**: Unified the fragmented terminal search output (`google-lens search <query> --enrich`) into an intuitive 3-tier hierarchy that mirrors the JSON response structure:
  1. **Executive Product Intelligence & Market Valuation Card**: An integrated Rich panel combining multimodal visual identification (brand, model, category, colorway, condition, est. MSRP) with aggregated market pricing analytics (listings analyzed, price range, average price, 🏆 best deal seller with clickable direct URL, resale outlook, and tags).
  2. **Commercial Products & Pricing Table**: A focused, deduplicated table displaying only verified commercial listings with AI evaluation badges, prices, and clickable clean destination URLs.
  3. **Metadata & Telemetry Footer**: Clean summary line of product/editorial/social breakdowns, export confirmations, and Gemini token cost telemetry.
- **Suppressed Redundant SERP Tables**: Suppressed the raw 20-row Google Lens visual matches table during enriched searches, eliminating duplicate listing dumps while retaining raw tables when `--no-enrich` is explicitly requested.

### Removed
- **Hardcoded Product Category Guesses**: Removed arbitrary domain keyword guessing (`"Running Shoes / Sneakers"`, `"Luxury Watches"`, `"Consumer Electronics"`) from native fallback deduction in `deduce_native_analysis()`. The engine now preserves Google Lens's authentic Knowledge Graph classification (`knowledge_graph.subtitle`) when available, and omits speculative category labels cleanly when unverified.
- **Domain-Specific Footwear Heuristics**: Removed hardcoded checks for `"shoes"`, `"sneakers"`, `"footwear"`, and `"nike"` from `CommerceEnricher` page type classification, restoring universal category-agnostic classification across all product verticals.
- **Static Merchant Title Cleaner Regex**: Replaced hardcoded 12-merchant regex (`GOAT`, `eBay`, `StockX`, `Amazon`, `Walmart`, `TheRealReal`, `Grailed`, `SeedProd`, `WooLentor`, `Shopify`, `B&H`, `Chrono24`) in title cleaning with dynamic candidate source, SLD, and domain matching.
- **Category Nouns in `GENERIC_TITLES`**: Removed category nouns (`"shoe"`, `"shoes"`, `"clothing"`, `"home"`) from `GENERIC_TITLES`, restricting generic title replacement strictly to universal CTA and placeholder anchor strings.

### Fixed
- **Fallback Native Product Deduction**: Fixed a bug where `deduce_native_analysis()` accepted generic SERP titles (e.g. `"Search Results"`) from `knowledge_graph.title` when Gemini API encountered a 503 error, which caused the brand to be extracted as `"Search"` and the model as `"Search Results"`, subsequently marking all legitimate commercial matches as `🚫 Noise`. Added generic SERP title filtering, OCR brand detection, and candidate title cross-referencing.
- **Gemini Transient Error Resilience**: Added automatic retry with backoff for transient 503 UNAVAILABLE and 429 RESOURCE_EXHAUSTED errors in `VisualAnalyzer.analyze()`, and expanded candidate fallback models to include `gemini-3.5-flash`.
- **CLI Table URL Truncation**: Fixed a bug where `Clean URL` and `Destination URL` columns in CLI terminal tables were being hard-sliced with `[:40]` and `[:50]`, corrupting URLs and causing 404 "page not found" errors when copied or clicked. Replaced with full OSC 8 hyperlinks (`[link=url]url[/link]`) and column `overflow="fold"`.
- **Gemini Automatic Function Calling (AFC) Warning**: Fixed Google GenAI SDK warning (`Direct use of automatic function calling (AFC) in Models.generate_content is not recommended`) by explicitly setting `automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)` on single-turn `GenerateContentConfig` objects in `VisualAnalyzer` and `StudioSynthesizer`.
- **Universal Next.js Out-of-Stock & Live Price Extraction**: Fixed a bug where Next.js hydration extraction prioritized catalog MSRP (`specialDisplayPriceCents` / `retailPriceCents`) over live transaction offers (`lowestPriceCents` / `price`), and hardcoded `StockStatus.IN_STOCK`. The engine now checks universal availability signals across Next.js payloads (seller counts, stock status flags, inventory levels, zero live price indicators), suppresses catalog MSRP when an item has no active sellers, and ensures market valuation `best_deal` selection strictly prefers in-stock purchase offers.

## [0.1.4] - 2026-09-06

### Added
- **Category-Agnostic AI Match Evaluation**: Replaced hardcoded category stop words and regexes with pure English grammatical particles. Bundled candidate match evaluations directly into Gemini 3.8 Flash's single multimodal analysis call, providing universal semantic classification (`exact_match`, `similar`, `reference`, `unrelated`) and human-readable reasoning (`ai_evaluation.reason`) across all product verticals (luxury watches, consumer electronics, footwear, apparel, furniture, tools, collectibles).
- **Clean Data Provenance Hierarchy**: Established a clear structural separation between scraped web facts (`match_score`, `price`, `page_type`, `brand`, `sku`, `merchant_name`, `direct_url`) and AI analytical judgments (`ai_evaluation: { "relevance", "reason" }`).
- **Contextual Target Product in Market Summary**: Added `CommerceSummary.target_product` to record the identified product that listings are evaluated against, displayed in both JSON export and CLI analytics tables.
- **Native Async Enrichment Pipeline (`enrich_async`)**: Added `enrich_async()` in `_pro.py` and `CommerceEnricher.process_async()`, allowing asynchronous applications to perform full e-commerce enrichment and pricing analytics without blocking the event loop.
- **Dynamic Gemini Billing Tiers & Cost Calculator**: Added `google-lens setup-ai --tier [unknown|free|paid]` to configure account-specific billing tiers with automatic token cost computation.

### Changed
- **CLI Table Layout & Alignment**: Streamlined `_build_commerce_table` to 7 high-signal columns (`Match Score`, `AI Eval`, `Brand`, `Title`, `Price`, `Merchant`, `Clean URL`), setting `min_width` and `no_wrap` to prevent column squishing and header collapsing in standard-width terminals.
- **JSON Serialization Cleanliness**: Added `exclude=True` to `VisualAnalysis.match_evaluations` so internal candidate schemas operate during generation while omitting the redundant 100-line detached index array from final `export.json`.
- **Backward Compatibility**: Added `@property` and `@relevance.setter` on `EnrichedCommerceMatch` with a Pydantic `model_validator(mode="before")` so existing code accessing or passing `item.relevance` continues to work seamlessly.

### Fixed
- **Type-Narrowing in Pricing Registry**: Fixed possible `NoneType` numeric conversion errors in `PricingRegistry.load_from_json()` when parsing custom JSON pricing overrides.

## [0.1.3] - 2026-09-05

### Fixed
- **Persistent License Cache & Background Revalidation**: Fixed a critical bug where the 12-hour offline validation cache TTL caused `get_configured_key()` to discard the user's stored license key, locking active Pro users into Preview Mode. Decoupled disk key persistence (`check_ttl=False`) from offline cache validity, added automatic background revalidation when online, and established a 7-day offline grace period (`OFFLINE_GRACE_PERIOD_SECONDS`).
- **High-Accuracy Merchant & Domain Classification**: Upgraded `MerchantClassifier` with clean second-level domain (SLD) extraction (`_extract_sld`), stripping multi-tenant subdomains (`www`, `store`, `shop`, `us`, etc.) and handling multi-part ccTLDs (`.co.uk`, `.com.ng`, `.co.ke`).
- **Multi-Token Fuzzy Brand Matching**: Implemented normalized alphanumeric and multi-token fuzzy matching against detected brand, merchant name, and title (e.g. matching `rmfhq.com` with `RMFHQ`, `fadoshoes.com` with `Fado Shoes`, and `woolentor.com` with `WooLentor`).
- **Enrichment Order & Non-Commercial Suppression**: Reordered enrichment so merchant classification runs after HTML metadata parsing. Set `merchant_category: MerchantCategory | None = None` to cleanly omit seller classifications on non-commercial pages (`article`, `social`, `portfolio`).
- **Expanded Page Intent Heuristics**: Added comprehensive URL path and keyword patterns for editorial guides (`/fashion/`, `/advice/`, `/insights/`), developer portfolios/templates (`/template/`, `/redesign/`, `github.io`), and store catalogs (`/categories/`, `/collections/`, `/w/`, `.shop`).
- **E-Commerce Variant & Price Fallbacks**: Added extraction support for Shopify variant groups (`hasVariant`), WooCommerce price spans, and microdata tags, restoring correct pricing for single-item and catalog teasers.

## [0.1.2] - 2026-09-05

### Added
- **JSON-First Architecture & Export**: Standardized on `--export-json` (and `--export`) for clean hierarchical JSON exports. Deprecated `--export-csv` to cleanly handle polymorphic Google Lens SERP listings without sparse, empty columns.
- **Deep Destination Page Intelligence**: Integrated concurrent async Scrapling fetching to extract Schema.org JSON-LD (`Product`, `ProductGroup`, `Offer`), Next.js hydration state (`__NEXT_DATA__`), and OpenGraph metadata.
- **Title Normalization & URL Sanitization**: Auto-unwraps Google redirect wrappers, strips tracking parameters (`utm_*`, `fbclid`, `gclid`), strips Chrome text fragments (`#:~:text=...`), and repairs generic or swapped titles (`"Read more"`).
- **Polymorphic Page Classification**: Added `PageType` classification (`product`, `marketplace`, `article`, `portfolio`, `social`, `uncategorized`) and category properties (`c.products`, `c.articles`, `c.social`) on `CommerceIntelligence`.
- **Focused CLI Product Intelligence**: Formatted terminal output now showcases verified commercial products (`c.products`) in pricing tables, with articles and social listings summarized in a clean breakdown line.

### Fixed
- **Anti-Bot & Fingerprint Masking**: Enforced authentic Chrome desktop User-Agent and Client Hints (`sec-ch-ua`, `sec-ch-ua-mobile`, `sec-ch-ua-platform`) across all sync and async browser contexts, completely eliminating `HeadlessChrome` detection leaks.
- **Session Cookie Propagation**: Automatically attach authenticated session cookies (`get_httpx_cookies()`) to `httpx.Client` requests, preventing anonymous vs. authenticated session mismatch flags on Google Lens ingestion.
- **DOM Card Price Extraction**: Updated `LensParser.extract_from_dom_cards` to climb parent card containers (`N54PNb`) and extract price badges placed outside `<a>` tags in modern Google Lens layouts.
- **Expanded Currency Recognition**: Broadened `_PRICE_PATTERN` to support prefix and suffix currency symbols (`$`, `€`, `£`, `¥`, `₹`, `USD`, `EUR`, `GBP`, `CAD`, `AUD`, `INR`) and comma/dot thousands separators.
- **Dynamic DOM Polling**: Replaced static CSS selector timeouts with `_wait_for_matches` live DOM polling, eliminating race conditions during asynchronous card hydration.
- **Interactive Security Clearance**: Enhanced `google-lens login` to launch with full stealth headers and navigate directly to Google Search, allowing users to solve pending reCAPTCHAs/unusual traffic challenges and capture cross-domain `OSID` tokens on `lens.google.com`.

## [0.1.1] - 2026-09-05

### Fixed
- Use absolute raw GitHub asset URLs in `README.md` so the project banner and UI divider lines render correctly on PyPI.
- Updated shields.io badge parameters to bypass proxy caching.
- Resolved Apple Silicon (`macos-14`) CI wheel builds with dynamic OpenSSL discovery and foreign-arch test skipping for cross-compiled Intel wheels.
- Moved `POLAR_LINKS` and paywall copy to MIT core (`_pro.py`) so `google-lens buy` works on all installations.

## [0.1.0] - 2026-09-05

First public release on PyPI.

### Added — Community Core (MIT)

- Dual-engine architecture:
  - Chromium native Protobuf fast path (`lensfrontend-pa.googleapis.com/v1/crupload`, via `chrome-lens-py`) for OCR, object detection, and session token extraction.
  - Scrapling/Patchright browser automation for visual match extraction.
- Query auto-classification across image URLs, local image files, raw image bytes, and Google search URLs.
- Synchronous `LensScraper` and asynchronous `AsyncLensScraper` client APIs.
- Typed Pydantic models: `LensSearchResult`, `VisualMatch`, `KnowledgeGraph`, `DetectedObject`, `BoundingBox`.
- Anti-bot mitigation: cookies (`SOCS` / `CONSENT` / `SID`), persistent Chrome profiles (`--profile-dir`), CDP attach (`--cdp-url`), and HTTP/SOCKS5 proxies.
- Session management via `SessionManager` and the `login`, `logout`, `session` (alias `status`), and `export-session` (alias `export`) commands, including `--base64`, and `--env` to write `LENS_STORAGE_STATE_JSON` into a local `.env`. `.env` files are detected automatically and base64 session state is decoded on load.
- CLI `google-lens`, with `google-lens-scraper` and `google-lens-pro` as aliases, offering formatted table and raw JSON output.
- `install-skill` to install the bundled `google-lens` agent skill into a project or user directory (`--dest`, `--global`, `--claude`, `--force`).
- `py.typed` marker; the package ships type information.

### Added — AI features (bring your own Gemini API key)

- `VisualAnalyzer` (`--analyze`): multimodal product attribute extraction using `gemini-3.8-flash`.
- `StudioSynthesizer` (`--studio`, `--studio-output`, `--studio-prompt`): studio packshot synthesis using `models/nano-banana-pro-preview`.
- `setup-ai` to store a Gemini API key in the user config directory (`$XDG_CONFIG_HOME/google-lens-scraper/config.json`, defaulting to `~/.config`).
- `gemini_cost_calculator` (`calculate_cost`, `UsageAccumulator`) for per-call token cost accounting.

### Added — Pro Commercial Intelligence (proprietary, requires a Polar.sh license key)

- `CommerceEnricher` (`--enrich`): canonical URL unwrapping (Google redirect decoding and tracking-parameter stripping), multi-currency price normalization, merchant categorization, and lowest-price best-deal detection.
- `export_commerce_to_json` and `--export-json` (alias `--export`) for hierarchical JSON export of enriched listings.
- Without an active license key, enrichment runs in preview mode: a single teaser listing, with pricing analytics and best-deal detection withheld.
- `LicenseManager` and the `pro` command group (`buy`, `activate`, `status`, `deactivate`), mirrored by the `license` group and by top-level `buy` / `activate` shortcuts; `upgrade` prints plans and opens checkout.
- License keys are read from `LENS_LICENSE_KEY` or `GOOGLE_LENS_LICENSE_KEY`, or from a local cache that permits 12 hours of offline validation.
- `PRO_AVAILABLE` is exported from the package so callers can detect whether the Pro engines are present; without them the core runs normally and enrichment is skipped.

### Packaging

- Dual-licensed: the Community Core is MIT, and the Pro modules (`license.py`, `commerce.py`) are proprietary. See [LICENSE](LICENSE).
- Published as binary wheels for CPython 3.10-3.14 on Linux (manylinux x86_64), macOS (arm64 and x86_64), and Windows (AMD64). The Pro modules are compiled to C extensions with mypyc and ship as `.pyi` stubs rather than source.

[Unreleased]: https://github.com/taazkareem/google-lens-scraper/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/taazkareem/google-lens-scraper/releases/tag/v0.1.0
