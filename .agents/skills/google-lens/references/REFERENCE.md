# Google Lens Scraper Reference Manual

This reference manual provides technical specifications, CLI flags, configuration environment variables, response data structures, and troubleshooting protocols for the `google-lens` skill.

---

## 1. CLI Commands & Options

### `google-lens search <QUERY> [OPTIONS]`
Performs visual match searches, OCR extraction, and Knowledge Graph entity lookups.
`QUERY` can be:
- A public image URL (e.g., `https://example.com/item.jpg`)
- A local image file path (e.g., `./images/product.png`, `~/receipt.jpg`)
- An existing Google Lens search result URL (`https://lens.google.com/search?p=...` or `google.com/search?udm=26...`)

| Option | Flag | Description | Default |
|---|---|---|---|
| `--json-output` | | Emit raw structured JSON to stdout (ideal for agents & scripts) | `False` |
| `--output` | `-o <path>` | Write structured JSON to a specified file | `None` |
| `--ocr-only` | | Fast-path OCR via Protobuf engine (zero browser overhead, zero CAPTCHAs) | `False` |
| `--enrich / --no-enrich` | | Canonical URLs, price normalization & best-deal arbitrage (Pro) | `True` |
| `--export-json` | `--export <path>` | Export enriched commerce intelligence to a JSON file (Pro) | `None` |
| `--analyze / --no-analyze` | | Deep multimodal attribute deduction via Gemini 3.8 Flash | `True` |
| `--studio` | | Synthesize 8K commercial product packshot via Nano Banana Pro | `False` |
| `--studio-output` | `<path>` | Output path for synthesized 8K packshot image | `None` |
| `--headless / --no-headless` | | Toggle browser visibility (stealth Chromium) | `True` |
| `--cookies` | `-c <str>` | Inline cookie string (`"SID=...; SOCS=..."`) | `None` |
| `--proxy` | `-p <url>` | HTTP or SOCKS5 proxy URL (`http://user:pass@host:port`) | `None` |
| `--profile-dir` | | Path to persistent Chrome user profile directory | `None` |
| `--cdp-url` | | Connect to existing Chrome instance via CDP (`http://localhost:9222`) | `None` |
| `--timeout` | | Maximum execution time in seconds | `30.0` |

### `google-lens status`
Inspects the saved authentication session. Displays:
- Storage state file location (`~/.config/google-lens-scraper/session.json`)
- Authentication state (`Authenticated` vs `Unauthenticated`)
- Number of loaded session cookies
- Security token presence (`SOCS`, `SID`, `HSID`, `NID`)

### `google-lens login [OPTIONS]`
Launches an interactive Chromium window to log into Google and saves session cookies for permanent headless search capability.
- `--timeout <int>`: Seconds to wait for Google login (default: `120`).
- `--env`: Automatically updates `LENS_STORAGE_STATE_JSON` in the local `.env` file.
- `--export`: Outputs the single-line base64 export string immediately upon clearance.

### `google-lens logout`
Deletes saved session cookies from `~/.config/google-lens-scraper/session.json`.

### `google-lens export-session [OPTIONS]`
Exports the authenticated session storage state for container, serverless, or CI/CD deployments.
- `--base64`: Prints single-line base64 string suitable for environment variables.
- `--env`: Appends or updates `LENS_STORAGE_STATE_JSON` in `.env`.

### `google-lens install-skill [OPTIONS]`
Exports and installs this Agent Skill into any local project or global agent directory.
- `--dest <path>`: Custom destination directory.
- `--global`, `-g`: Installs to `~/.agents/skills/google-lens/` (user home).
- `--claude`: Installs to Claude Code directory (`.claude/skills/google-lens/` or `~/.claude/skills/google-lens/`).
- `--force`, `-f`: Overwrites target directory if it already exists.

### `google-lens setup-ai [OPTIONS]`
Manages Google AI Studio Gemini API key and billing tier configuration for cost accounting.
- `--key <str>`: Persist Gemini API key in local configuration.
- `--tier <tier>`: Set billing tier for cost telemetry (`unknown`, `free`, or `paid`).
- `--status`: Display current configured API key and billing tier.
- `--clear`: Remove saved Gemini API key and reset billing tier.

---

## 2. Environment Variables

The package automatically checks the local `.env` file in the working directory before falling back to system environment variables.

| Variable | Description |
|---|---|
| `LENS_STORAGE_STATE_JSON` | Single-line base64 string or raw JSON of Playwright storage state containing authenticated Google cookies. |
| `LENS_STORAGE_STATE_PATH` | Path on disk to a valid storage state JSON file (e.g. `/secrets/session.json`). |
| `LENS_COOKIES` | Raw cookie header string (e.g., `"SID=...; SOCS=..."`). |
| `LENS_PROXY` | Proxy endpoint URL (e.g., `http://proxy.example.com:8080`). |
| `LENS_HEADLESS` | Set to `"false"` or `"0"` to run Chromium in headed mode for visual debugging. |
| `LENS_TIMEOUT` | Default request timeout in seconds (default: `30.0`). |
| `GEMINI_API_KEY` | Google AI Studio API key used for 8K studio packshot generation and multimodal visual analysis. |
| `GEMINI_BILLING_TIER` | Billing tier (`unknown`, `free`, or `paid`) for real-time USD cost accounting. |

---

## 3. Data Models & JSON Schema

All search results are validated by Pydantic models. Calling `.to_json()` or passing `--json-output` yields the following schema:

### `LensSearchResult`
```json
{
  "query": "string (URL or file path)",
  "page_url": "string (Google Lens search URL)",
  "ocr_text": "string | null (Full concatenated OCR text extracted from image)",
  "knowledge_graph": {
    "title": "string (e.g. 'Air Jordan 1')",
    "subtitle": "string | null (e.g. 'Sneakers')",
    "description": "string | null",
    "website": "string | null (Entity link or Wikipedia URL)"
  },
  "commerce": {
    "summary": {
      "target_product": "string | null (Identified canonical product name)",
      "total_matches": 69,
      "total_priced_matches": 1,
      "min_price": 120.0,
      "max_price": 120.0,
      "avg_price": 120.0,
      "currency": "USD",
      "best_deal": {
        "title": "string",
        "direct_url": "string (Clean canonical merchant URL)",
        "price": { "raw": "$120.00", "amount": 120.0, "currency": "USD" },
        "merchant_name": "string",
        "match_score": 97,
        "relevance": "exact_match",
        "relevance_reason": "string"
      }
    },
    "items": [
      {
        "title": "string",
        "direct_url": "string",
        "match_score": 97,
        "relevance": "exact_match | similar | reference | unrelated",
        "relevance_reason": "string | null",
        "page_type": "product | marketplace | article | social | portfolio | uncategorized",
        "price": { "raw": "string", "amount": 0.0, "currency": "USD" },
        "merchant_name": "string | null",
        "brand": "string | null",
        "sku": "string | null",
        "condition": "new | used | refurbished | null",
        "stock_status": "in_stock | out_of_stock | preorder | null"
      }
    ]
  },
  "visual_matches": [
    {
      "title": "string (Visual match heading)",
      "link": "string (Destination source URL)",
      "source": "string | null (Publisher / store name, e.g. 'eBay', 'Amazon')",
      "price": "string | null (Price if shopping match, e.g. '$120.00')",
      "thumbnail": "string | null (Google thumbnail CDN URL)"
    }
  ],
  "detected_objects": [
    {
      "id": "string",
      "bounding_box": {
        "center_x": "float (0.0 to 1.0)",
        "center_y": "float (0.0 to 1.0)",
        "width": "float (0.0 to 1.0)",
        "height": "float (0.0 to 1.0)"
      }
    }
  ],
  "cost": {
    "model": "string",
    "calls_count": 1,
    "tokens": { "prompt": 450, "output": 180, "total": 630 },
    "cost_usd": { "total": 0.001013 }
  }
}
```

---

## 4. Headless & Production Authentication

Modern Google Lens layouts apply heuristic bot defenses against unauthenticated headless scrapers.
To maintain 100% reliability in production:

1. **Local Authentication**: Run `google-lens login --env` once on a machine with a display.
2. **Transfer to Production**: Copy the base64 token generated in `.env` (`LENS_STORAGE_STATE_JSON="..."`) into your production environment variables, Kubernetes secret, or Docker environment (`docker run -e LENS_STORAGE_STATE_JSON="..."`).
3. **No-Browser Fallback**: In restricted headless environments with zero cookies available, use `--ocr-only`. This route bypasses the browser completely, utilizing Chromium's internal Protobuf RPC protocol (`v1/crupload`) to return OCR and object tags with zero CAPTCHA exposure.
