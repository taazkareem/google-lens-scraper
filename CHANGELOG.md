# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
- `export_commerce_to_csv` and `--export-csv` for CSV export of enriched listings.
- Without an active license key, enrichment runs in preview mode: a single teaser listing, with pricing analytics and best-deal detection withheld.
- `LicenseManager` and the `pro` command group (`buy`, `activate`, `status`, `deactivate`), mirrored by the `license` group and by top-level `buy` / `activate` shortcuts; `upgrade` prints plans and opens checkout.
- License keys are read from `LENS_LICENSE_KEY` or `GOOGLE_LENS_LICENSE_KEY`, or from a local cache that permits 12 hours of offline validation.
- `PRO_AVAILABLE` is exported from the package so callers can detect whether the Pro engines are present; without them the core runs normally and enrichment is skipped.

### Packaging

- Dual-licensed: the Community Core is MIT, and the Pro modules (`license.py`, `commerce.py`) are proprietary. See [LICENSE](LICENSE).
- Published as binary wheels for CPython 3.10-3.14 on Linux (manylinux x86_64), macOS (arm64 and x86_64), and Windows (AMD64). The Pro modules are compiled to C extensions with mypyc and ship as `.pyi` stubs rather than source.

[Unreleased]: https://github.com/taazkareem/google-lens-scraper/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/taazkareem/google-lens-scraper/releases/tag/v0.1.0
