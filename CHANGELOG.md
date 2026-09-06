# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
