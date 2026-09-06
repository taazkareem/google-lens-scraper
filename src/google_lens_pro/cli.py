"""Command-line interface for Google Lens Scraper."""

from __future__ import annotations

import base64
import contextlib
import importlib.resources as pkg_resources
import json
import shutil
import sys
import webbrowser
from pathlib import Path

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from . import _pro
from ._query import classify_query
from .client import GoogleLens, LensScraper
from .config import LensConfig
from .exceptions import LensError, LensRateLimitError
from .models import (
    EnrichedCommerceMatch,
    LensSearchResult,
    MatchRelevance,
    ShoppingOffer,
    ShoppingResult,
)
from .parser import PROG_NAME
from .session import SessionManager

console = Console()
stderr_console = Console(stderr=True)


def _require_pro() -> None:
    """Stops a Pro-only command cleanly when the Pro engines are not installed."""
    if not _pro.AVAILABLE:
        raise click.ClickException(
            "Google Lens Pro engines are not part of the MIT source tree. "
            "Install the published package instead: pip install google-lens-pro"
        )


def _build_commerce_table(title: str, items: list[EnrichedCommerceMatch]) -> Table:
    """Builds the shared Rich table layout used for both preview and full commerce listings."""
    table = Table(title=title)
    table.add_column("Match Score", style="bold green", justify="right", min_width=11, no_wrap=True)
    table.add_column("AI Eval", style="bold yellow", min_width=10, no_wrap=True)
    table.add_column("Brand", style="yellow", min_width=8, max_width=14)
    table.add_column("Title", style="bold white", min_width=20, max_width=32)
    table.add_column("Price", style="bold green", min_width=10, no_wrap=True)
    table.add_column("Merchant", style="cyan", min_width=10, max_width=16)
    table.add_column("Clean URL", style="blue", min_width=20, overflow="fold")

    for item in items:
        price_str = (
            f"{item.price.amount:.2f} {item.price.currency}" if item.price else "[dim]—[/dim]"
        )
        rel = item.relevance
        if rel == MatchRelevance.EXACT_MATCH:
            rel_str = "[bold green]🎯 Exact[/bold green]"
        elif rel == MatchRelevance.SIMILAR:
            rel_str = "[cyan]🔄 Similar[/cyan]"
        elif rel == MatchRelevance.REFERENCE:
            rel_str = "[dim]📄 Ref[/dim]"
        elif rel == MatchRelevance.UNRELATED:
            rel_str = "[dim red]🚫 Noise[/dim red]"
        else:
            rel_str = "[dim]—[/dim]"

        brand_str = item.brand if item.brand else "[dim]—[/dim]"
        merchant_str = item.merchant_name or "[dim]—[/dim]"
        url_str = (
            f"[link={item.direct_url}]{item.direct_url}[/link]"
            if item.direct_url
            else "[dim]—[/dim]"
        )

        table.add_row(
            f"{item.match_score}%",
            rel_str,
            brand_str,
            item.title[:32],
            price_str,
            merchant_str,
            url_str,
        )
    return table


def _build_shopping_table(title: str, offers: list[ShoppingOffer]) -> Table:
    """Builds a rich table of verified Google Shopping merchant listings."""
    table = Table(title=title)
    table.add_column("Rank", style="dim", justify="right", width=5)
    table.add_column("Store / Seller", style="bold cyan", min_width=12, max_width=20)
    table.add_column("Title", style="bold white", min_width=20, max_width=36)
    table.add_column("Price", style="bold green", min_width=10, no_wrap=True)
    table.add_column("Shipping", style="dim green", min_width=10)
    table.add_column("Rating", style="yellow", min_width=8)
    table.add_column("Direct Store Link", style="blue", min_width=20, overflow="fold")

    for idx, offer in enumerate(offers, 1):
        price_str = (
            f"{offer.price.amount:.2f} {offer.price.currency}"
            if offer.price
            else "[dim]—[/dim]"
        )
        ship_str = offer.shipping_info or "[dim]Standard[/dim]"
        rating_str = f"★ {offer.rating:.1f}" if offer.rating else "[dim]—[/dim]"
        if offer.review_count:
            rating_str += f" ({offer.review_count})"
        url_str = (
            f"[link={offer.direct_url}]{offer.direct_url}[/link]"
            if offer.direct_url
            else "[dim]—[/dim]"
        )

        table.add_row(
            str(idx),
            offer.merchant_name or "Store",
            offer.title[:36],
            price_str,
            ship_str,
            rating_str,
            url_str,
        )
    return table


def _build_shopping_panel(result: ShoppingResult) -> Panel:
    """Builds an executive market valuation panel for Google Shopping results."""
    grid = Table.grid(padding=(0, 3), expand=True)
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)

    left = Table.grid(padding=(0, 1))
    left.add_column(style="bold cyan", no_wrap=True)
    left.add_column(style="white")
    left.add_row("Product Query:", f"[bold white]{result.query}[/bold white]")
    left.add_row("Offers Detected:", f"[bold green]{result.total_offers}[/bold green]")
    curr = result.currency or "USD"
    if result.min_price is not None and result.max_price is not None:
        left.add_row(
            "Price Range:",
            f"[green]{result.min_price:.2f} – {result.max_price:.2f} {curr}[/green]",
        )
    if result.avg_price is not None:
        left.add_row("Average Price:", f"[bold]{result.avg_price:.2f} {curr}[/bold]")

    right = Table.grid(padding=(0, 1))
    right.add_column(style="bold yellow", no_wrap=True)
    right.add_column(style="white")
    if result.best_deal and result.best_deal.price:
        deal = result.best_deal
        right.add_row(
            "🏆 Best Deal:",
            f"[bold green]{deal.price.amount:.2f} {deal.price.currency}[/bold green]",
        )
        right.add_row("Best Seller:", f"[bold cyan]{deal.merchant_name}[/bold cyan]")
        if deal.shipping_info:
            right.add_row("Shipping:", f"[dim]{deal.shipping_info}[/dim]")
        if deal.direct_url:
            right.add_row("Direct Link:", f"[link={deal.direct_url}]{deal.direct_url}[/link]")

    grid.add_row(left, right)
    return Panel(
        grid,
        title=f"🛒 Google Shopping Market Intelligence: {result.query}",
        border_style="green",
    )


def _build_executive_panel(results: LensSearchResult) -> Panel:
    """Builds a unified Executive Product Intelligence & Market Valuation card."""
    c = results.commerce
    s = c.summary if c else None
    a = results.analysis
    attrs = a.attributes if a else None

    grid = Table.grid(padding=(0, 3), expand=True)
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)

    left = Table.grid(padding=(0, 1))
    left.add_column(style="bold cyan", no_wrap=True)
    left.add_column(style="white")

    if attrs:
        if attrs.brand:
            left.add_row("Brand:", attrs.brand)
        if attrs.model_or_name:
            left.add_row("Model / Silhouette:", attrs.model_or_name)
        if attrs.category:
            left.add_row("Category:", attrs.category)
        if attrs.color:
            left.add_row("Colorway:", attrs.color)
        if attrs.condition_assessment:
            left.add_row("Condition:", attrs.condition_assessment)
        if attrs.estimated_msrp_usd is not None:
            conf_str = (
                f" [dim]({attrs.confidence_score * 100:.0f}% conf)[/dim]"
                if attrs.confidence_score
                else ""
            )
            left.add_row("Est. MSRP:", f"${attrs.estimated_msrp_usd:,.2f} USD{conf_str}")
        elif attrs.confidence_score:
            left.add_row("Confidence:", f"{attrs.confidence_score * 100:.0f}%")
        if attrs.materials:
            left.add_row("Materials:", ", ".join(attrs.materials))
        if results.ocr_text:
            clean_ocr = " ".join(results.ocr_text.split())
            if len(clean_ocr) > 35:
                clean_ocr = clean_ocr[:32] + "..."
            if clean_ocr.lower() not in (attrs.brand or "").lower():
                left.add_row("OCR Text:", f'[dim]"{clean_ocr}"[/dim]')
    else:
        target_name = (
            (s.target_product if s else None)
            or (
                results.knowledge_graph.title
                if (
                    results.knowledge_graph
                    and results.knowledge_graph.title
                    and results.knowledge_graph.title.lower()
                    not in ("search results", "visual matches")
                )
                else None
            )
            or "Visual Search Target"
        )
        left.add_row("Target Product:", f"[bold yellow]{target_name}[/bold yellow]")
        if results.knowledge_graph and results.knowledge_graph.subtitle:
            left.add_row("Entity Category:", results.knowledge_graph.subtitle)
        if results.ocr_text:
            clean_ocr = " ".join(results.ocr_text.split())
            if len(clean_ocr) > 40:
                clean_ocr = clean_ocr[:37] + "..."
            left.add_row("Detected Text:", f'[dim]"{clean_ocr}"[/dim]')

    right = Table.grid(padding=(0, 1))
    right.add_column(style="bold green", no_wrap=True)
    right.add_column(style="white", overflow="fold")

    if s:
        priced_suffix = f" ({s.total_priced_matches} priced)" if s.total_priced_matches else ""
        right.add_row("Listings Analyzed:", f"{s.total_matches}{priced_suffix}")
        if s.min_price is not None and s.max_price is not None:
            if s.min_price == s.max_price:
                range_str = f"{s.min_price:.2f} {s.currency}"
            else:
                range_str = f"{s.min_price:.2f} – {s.max_price:.2f} {s.currency}"
            right.add_row("Market Price Range:", range_str)
        if s.avg_price is not None:
            right.add_row("Average Market Price:", f"{s.avg_price:.2f} {s.currency}")
        if s.best_deal:
            deal_amt = (
                f"{s.best_deal.price.amount:.2f} {s.currency}" if s.best_deal.price else "N/A"
            )
            merchant = s.best_deal.merchant_name or "Direct"
            right.add_row(
                "🏆 Best Deal Seller:", f"[bold yellow]{merchant}[/bold yellow] ({deal_amt})"
            )
            if s.best_deal.direct_url:
                right.add_row(
                    "",
                    f"[link={s.best_deal.direct_url}][blue]{s.best_deal.direct_url}[/blue][/link]",
                )
    elif results.visual_matches:
        right.add_row("Visual Matches:", f"{len(results.visual_matches)} matches found")

    grid.add_row(left, right)

    content = Table.grid()
    content.add_column()
    if a and a.summary:
        content.add_row(f"[italic]{a.summary}[/italic]\n")
    content.add_row(grid)

    if a:
        if a.resale_recommendation:
            content.add_row(
                f"\n[bold yellow]Resale Outlook:[/bold yellow] [dim]{a.resale_recommendation}[/dim]"
            )
        if attrs and attrs.key_features:
            features_str = " • ".join(attrs.key_features)
            content.add_row(f"[dim]Key Features: {features_str}[/dim]")
        if attrs and attrs.authenticity_markers:
            markers_str = " • ".join(attrs.authenticity_markers)
            content.add_row(f"[dim]Authenticity Markers: {markers_str}[/dim]")
        if a.tags:
            tag_str = " ".join(f"#{t.strip().replace(' ', '')}" for t in a.tags[:8])
            content.add_row(f"[dim]Tags: {tag_str}[/dim]")

    panel_title = (
        "✨ Google Lens Pro — Product Intelligence & Market Valuation"
        if (c and not c.is_preview)
        else "🧠 Multimodal Visual & Market Intelligence"
    )
    return Panel(
        content, title=f"[bold cyan]{panel_title}[/bold cyan]", border_style="cyan"
    )


class DefaultGroup(click.Group):
    """Click group that defaults to the 'search' subcommand when query is passed directly."""

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        if not args:
            return super().resolve_command(ctx, args)

        cmd_name = args[0]
        # If the argument is an option flag (e.g. --help, -h)
        if cmd_name.startswith("-") and cmd_name not in ("-h", "--help"):
            return "search", self.get_command(ctx, "search"), args

        # If it's a known explicit command
        if cmd_name in self.commands or cmd_name in ("-h", "--help"):
            return super().resolve_command(ctx, args)

        # Otherwise, assume it's a direct query: route text to 'shop' and images/files to 'search'
        kind, _ = classify_query(cmd_name)
        target = "shop" if kind == "text" else "search"
        return target, self.get_command(ctx, target), args


@click.group(cls=DefaultGroup, invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Google Lens Scraper - Reverse visual search, OCR, and Knowledge Graph extraction."""
    if ctx.invoked_subcommand is None and len(sys.argv) == 1:
        click.echo(ctx.get_help())


def _write_env_file(b64_data: str) -> Path:
    """Safely updates or appends LENS_STORAGE_STATE_JSON in the local .env file."""
    env_path = Path.cwd() / ".env"
    key = "LENS_STORAGE_STATE_JSON"
    new_line = f'{key}="{b64_data}"'
    lines: list[str] = []
    found = False

    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
                lines.append(new_line)
                found = True
            else:
                lines.append(line)

    if not found:
        lines.append(new_line)

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return env_path


@cli.command(name="login")
@click.option(
    "--timeout", default=120, help="Maximum seconds to wait for Google clearance (default: 120)"
)
@click.option(
    "--env",
    "write_env",
    is_flag=True,
    help="Automatically write or update LENS_STORAGE_STATE_JSON in the local .env file",
)
@click.option(
    "--export",
    "do_export",
    is_flag=True,
    help="Print base64 export string immediately after successful login",
)
def login_cmd(timeout: int, write_env: bool, do_export: bool) -> None:
    """Authenticate with Google once to save session cookies for headless visual search."""
    sm = SessionManager()
    console.print("[bold cyan]Google Lens Authentication[/bold cyan]")
    console.print("Launching a browser window to capture session credentials...")
    try:
        saved_path = sm.interactive_login(timeout_seconds=timeout)
        console.print(
            f"[bold green]✓ Session successfully established and saved to:[/bold green] {saved_path}"
        )
        console.print("[dim]You can now run headless visual searches with zero flags.[/dim]")

        if write_env or do_export:
            data = sm.load_session()
            if data:
                b64 = base64.b64encode(json.dumps(data).encode("utf-8")).decode("utf-8")
                if write_env:
                    p = _write_env_file(b64)
                    console.print(f"[bold green]✓ Saved credentials directly to:[/bold green] {p}")
                if do_export:
                    console.print("[bold cyan]Base64 Session Token:[/bold cyan]")
                    click.echo(b64)
        else:
            console.print(
                "[dim]To deploy this session to Docker or cloud, export as an env var:\n"
                f"  {PROG_NAME} export-session --env    (write directly to .env)\n"
                f"  {PROG_NAME} export-session --base64 (print token to stdout)[/dim]"
            )
    except Exception as e:
        console.print(f"[bold red]Authentication failed:[/bold red] {e}")
        sys.exit(1)


@cli.command(name="logout")
def logout_cmd() -> None:
    """Clear saved Google session tokens."""
    sm = SessionManager()
    if sm.clear_session():
        console.print("[bold green]✓ Saved Google session cleared.[/bold green]")
    else:
        console.print("[yellow]No active session file found.[/yellow]")


@cli.command(name="session")
def session_cmd() -> None:
    """Inspect the current saved Google authentication session."""
    sm = SessionManager()
    data = sm.load_session()
    is_auth = sm.is_authenticated()

    console.print(f"[bold cyan]Session File:[/bold cyan] {sm.session_path}")
    if not data or not is_auth:
        console.print("[yellow]Status: Unauthenticated (No valid Google cookies saved)[/yellow]")
        console.print(f"[dim]Run '{PROG_NAME} login' to authenticate.[/dim]")
        return

    cookies = data.get("cookies", [])
    console.print(f"[bold green]Status: Authenticated ({len(cookies)} cookies loaded)[/bold green]")
    key_cookies = [
        c["name"] for c in cookies if c.get("name") in ("SOCS", "SID", "NID", "AEC", "1P_JAR")
    ]
    console.print(f"[dim]Security Tokens Present: {', '.join(key_cookies)}[/dim]")


cli.add_command(session_cmd, name="status")


@cli.command(name="export-session")
@click.option(
    "--base64-only",
    "--base64",
    "base64_only",
    is_flag=True,
    help="Output a single-line base64 string for setting LENS_STORAGE_STATE_JSON in .env or cloud secrets",
)
@click.option(
    "--env",
    "write_env",
    is_flag=True,
    help="Automatically write or update LENS_STORAGE_STATE_JSON in the local .env file",
)
def export_cmd(base64_only: bool, write_env: bool) -> None:
    """Export the active authentication session state (cookies & storage) for cloud, Docker, or CI/CD deployment.

    Outputs the browser storage state JSON containing authenticated Google cookies.
    With --base64 / --base64-only, outputs a clean, single-line string that can be pasted directly
    into .env files, Docker environment variables, Kubernetes secrets, or GitHub Actions.
    With --env, automatically creates or updates the local .env file.
    """
    sm = SessionManager()
    data = sm.load_session()
    if not data:
        console.print(
            f"[bold red]Error:[/bold red] No saved session to export. Run '{PROG_NAME} login' first."
        )
        sys.exit(1)

    raw_json = json.dumps(data)
    b64 = base64.b64encode(raw_json.encode("utf-8")).decode("utf-8")

    if write_env:
        p = _write_env_file(b64)
        console.print(f"[bold green]✓ Session credentials written to:[/bold green] {p}")
        return

    if base64_only:
        click.echo(b64)
    else:
        click.echo(raw_json)


# Backwards compatibility alias
cli.add_command(export_cmd, name="export")


@cli.command(name="shop")
@click.argument("query", required=True)
@click.option("--country", default="US", help="Target country code (e.g. US, UK, CA, DE, FR)")
@click.option("--currency", default="USD", help="Target currency code (e.g. USD, EUR, GBP, CAD)")
@click.option(
    "--deep", is_flag=True, help="Deep scrape multi-seller comparison tables (/shopping/product/...)"
)
@click.option("--max-results", default=40, help="Maximum offers to extract (default: 40)")
@click.option("--json", "--json-output", "json_output", is_flag=True, help="Output formatted JSON to stdout")
@click.option(
    "--export-csv",
    type=click.Path(dir_okay=False, writable=True),
    help="Save offers to CSV file",
)
@click.option(
    "--export-json",
    type=click.Path(dir_okay=False, writable=True),
    help="Save offers to JSON file",
)
@click.option(
    "--headless/--no-headless",
    default=True,
    help="Run browser in headless mode if challenge occurs",
)
@click.option("-p", "--proxy", help="HTTP or SOCKS5 proxy URL")
@click.option("--timeout", default=30.0, help="Request timeout in seconds")
def shop_cmd(
    query: str,
    country: str,
    currency: str,
    deep: bool,
    max_results: int,
    json_output: bool,
    export_csv: str | None,
    export_json: str | None,
    headless: bool,
    proxy: str | None,
    timeout: float,
) -> None:
    """Search Google Shopping directly for verified merchant prices, stock, and store links.

    QUERY can be a product title, model, brand, or barcode/UPC.
    """
    config = LensConfig(
        headless=headless,
        timeout=timeout,
        proxy=proxy,
        country=country,
        currency=currency,
    )
    from .engines.shopping.engine import ShoppingEngine

    engine = ShoppingEngine(config=config)

    if not json_output and stderr_console.is_terminal:
        with stderr_console.status(
            f"[bold cyan]Searching Google Shopping for '{query}'...[/bold cyan]",
            spinner="dots",
        ) as status:

            def _update_status(msg: str) -> None:
                status.update(f"[bold cyan]{msg}[/bold cyan]")

            results = engine.search(
                query=query,
                country=country,
                currency=currency,
                deep=deep,
                max_results=max_results,
                on_progress=_update_status,
            )
    else:
        results = engine.search(
            query=query,
            country=country,
            currency=currency,
            deep=deep,
            max_results=max_results,
        )

    if json_output:
        click.echo(results.to_json())
        return

    console.print(_build_shopping_panel(results))
    if results.offers:
        console.print(
            _build_shopping_table(
                f"Verified Google Shopping Store Offers ({len(results.offers)})", results.offers
            )
        )

    if export_json:
        p = Path(export_json).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(results.to_json(), encoding="utf-8")
        console.print(f"[bold green]✓ Exported Google Shopping results to:[/bold green] {p}")

    if export_csv:
        p = Path(export_csv).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        import csv

        with p.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Rank",
                    "Store",
                    "Title",
                    "Price",
                    "Currency",
                    "Shipping",
                    "Rating",
                    "Review Count",
                    "Condition",
                    "Direct URL",
                ]
            )
            for idx, o in enumerate(results.offers, 1):
                writer.writerow(
                    [
                        idx,
                        o.merchant_name,
                        o.title,
                        o.price.amount if o.price else "",
                        o.price.currency if o.price else "",
                        o.shipping_info or "",
                        o.rating or "",
                        o.review_count or "",
                        o.condition.value if o.condition else "",
                        o.direct_url,
                    ]
                )
        console.print(f"[bold green]✓ Exported Google Shopping CSV to:[/bold green] {p}")


@cli.command(name="search")
@click.argument("query", required=True)
@click.option(
    "-o", "--output", help="Save structured results to a JSON file", type=click.Path(writable=True)
)
@click.option("--json-output", is_flag=True, help="Output raw JSON to stdout")
@click.option(
    "--ocr-only",
    is_flag=True,
    help="Fast-path OCR and object detection only via Protobuf (guaranteed zero CAPTCHAs)",
)
@click.option(
    "--enrich/--no-enrich",
    default=True,
    help="Enrich results with canonical URLs, pricing analytics, and merchant categorization (Pro)",
)
@click.option(
    "--analyze/--no-analyze",
    default=True,
    help="Extract deep multimodal product attributes via Gemini 3.8 Flash when GEMINI_API_KEY is present",
)
@click.option(
    "--studio",
    is_flag=True,
    help="Synthesize an 8K commercial product packshot via Nano Banana Pro",
)
@click.option(
    "--studio-output",
    type=click.Path(dir_okay=False, writable=True),
    help="Target file path to save synthesized 8K studio packshot",
)
@click.option(
    "--studio-prompt",
    type=str,
    help="Custom prompt for Nano Banana Pro studio packshot synthesis",
)
@click.option(
    "--export",
    "--export-json",
    "export_json",
    type=click.Path(dir_okay=False, writable=True),
    help="Export enriched commerce data to a structured JSON file (Pro)",
)
@click.option(
    "--export-csv",
    type=click.Path(dir_okay=False, writable=True),
    help="Deprecated: CSV export is deprecated, use --export-json",
    hidden=True,
)
@click.option(
    "--headless/--no-headless", default=True, help="Run browser in headless mode (default: True)"
)
@click.option("-c", "--cookies", help="Cookie header string (e.g. 'SOCS=...; SID=...')")
@click.option("-p", "--proxy", help="HTTP or SOCKS5 proxy URL")
@click.option("--profile-dir", help="Path to Chrome user data directory for session persistence")
@click.option(
    "--cdp-url", help="Connect to an existing Chrome browser over CDP (e.g. http://localhost:9222)"
)
@click.option("--country", default="US", help="Target country code for localization (e.g. US, UK, CA, DE, FR)")
@click.option("--currency", default="USD", help="Target currency code (e.g. USD, EUR, GBP, CAD)")
@click.option("--deep", is_flag=True, help="Deep scrape multi-seller comparative product tables")
@click.option("--timeout", default=30.0, help="Request timeout in seconds")
@click.pass_context
def search_cmd(
    ctx: click.Context,
    query: str,
    output: str | None,
    json_output: bool,
    ocr_only: bool,
    enrich: bool,
    analyze: bool,
    studio: bool,
    studio_output: str | None,
    studio_prompt: str | None,
    export_csv: str | None,
    export_json: str | None,
    headless: bool,
    cookies: str | None,
    proxy: str | None,
    profile_dir: str | None,
    cdp_url: str | None,
    country: str,
    currency: str,
    deep: bool,
    timeout: float,
) -> None:
    """Search Google Lens for visual matches, OCR text, and entities.

    QUERY can be a public image URL, local image file path, Google Lens search URL, or text query.
    """
    # Smart text query routing: if input is a text string / product title, forward to Google Shopping
    kind, value = classify_query(query)
    if kind == "text":
        if not json_output:
            console.print(f"[bold cyan]Routing text query to Google Shopping:[/bold cyan] {query}")
        return ctx.invoke(
            shop_cmd,
            query=query,
            country=country,
            currency=currency,
            deep=deep,
            max_results=40,
            json_output=json_output,
            export_csv=export_csv,
            export_json=export_json,
            headless=headless,
            proxy=proxy,
            timeout=timeout,
        )

    config = LensConfig(
        headless=headless,
        timeout=timeout,
        cookies=cookies,
        proxy=proxy,
        user_data_dir=profile_dir,
        cdp_url=cdp_url,
        country=country,
        currency=currency,
    )

    scraper = LensScraper(config=config)

    if not json_output:
        mode = (
            "OCR & Object Detection"
            if ocr_only
            else ("Full Visual Search (Enriched)" if enrich else "Full Visual Search")
        )
        console.print(f"[bold cyan]Querying Google Lens ({mode}):[/bold cyan] {query}")
        sm = config.get_session_manager()
        if not ocr_only and not sm.is_authenticated() and not cookies and not proxy and not cdp_url:
            console.print(
                "[yellow]Notice: No saved Google authentication session found. "
                "Unauthenticated searches may be challenged or delayed by Google.[/yellow]"
            )
            console.print(
                f"[dim]Tip: Run '{PROG_NAME} login' once to sign into Google and enable instant visual matches.[/dim]\n"
            )

    if studio and not json_output:
        from .settings import get_gemini_api_key, set_gemini_api_key

        if not get_gemini_api_key():
            console.print("\n[bold magenta]🎨 Nano Banana Pro 8K Studio[/bold magenta]")
            console.print(
                "Synthesizing 8K commercial product packshots requires a free Google AI Studio key.\n"
                "[dim]Get a free key in 10 seconds at: https://aistudio.google.com/app/apikey[/dim]\n"
            )
            with contextlib.suppress(Exception):
                entered_key = click.prompt(
                    "Enter your Gemini API key (or press Enter to skip)",
                    default="",
                    hide_input=True,
                )
                if entered_key and entered_key.strip():
                    set_gemini_api_key(entered_key.strip())
                    console.print(
                        "[bold green]✓ Key saved to local config. Proceeding with generation...[/bold green]\n"
                    )

    try:
        if not json_output and stderr_console.is_terminal:
            with stderr_console.status(
                "[bold cyan]Connecting to Google Lens...[/bold cyan]",
                spinner="dots",
            ) as status:

                def _update_status(msg: str) -> None:
                    status.update(f"[bold cyan]{msg}[/bold cyan]")

                results = (
                    scraper.detect(query, on_progress=_update_status)
                    if ocr_only
                    else scraper.search(
                        query,
                        enrich=enrich,
                        analyze=analyze,
                        studio=studio,
                        studio_output=studio_output,
                        studio_prompt=studio_prompt,
                        on_progress=_update_status,
                    )
                )
        else:
            results = (
                scraper.detect(query)
                if ocr_only
                else scraper.search(
                    query,
                    enrich=enrich,
                    analyze=analyze,
                    studio=studio,
                    studio_output=studio_output,
                    studio_prompt=studio_prompt,
                )
            )

        if json_output:
            click.echo(results.to_json())
            return

        # 1. Fast-path OCR and object detection mode
        if ocr_only:
            if results.ocr_text:
                console.print("\n[bold green]Detected OCR Text:[/bold green]")
                console.print(f"[dim]{results.ocr_text}[/dim]")

            if results.detected_objects:
                console.print(
                    f"\n[bold green]Detected Objects/Regions:[/bold green] {len(results.detected_objects)}"
                )
                for obj in results.detected_objects:
                    bounds = (
                        f"cx={obj.bounding_box.center_x:.2f}, cy={obj.bounding_box.center_y:.2f}"
                        if obj.bounding_box
                        else "N/A"
                    )
                    console.print(f"  • [cyan]{obj.id}[/cyan] ({bounds})")
            return

        # 2. Pro Commerce Intelligence Mode (when enrich is active and commerce data exists)
        if enrich and results.commerce:
            c = results.commerce
            if c.is_preview:
                console.print(
                    "\n[bold magenta]✨ Google Lens Pro — Commerce Intelligence (Preview)[/bold magenta]"
                )
                if c.items:
                    console.print(
                        _build_commerce_table(
                            "Deep Enriched Listing Preview (1-Item Teaser)", c.items[:1]
                        )
                    )
                if c.upgrade_message:
                    console.print(
                        Panel(
                            Markdown(c.upgrade_message),
                            border_style="magenta",
                            title="🔒 Unlock All Deals & Full Resale Analytics",
                        )
                    )
            else:
                # Render the unified Executive Product Intelligence & Market Valuation card
                console.print(_build_executive_panel(results))

                # Render verified commercial listings
                if c.items:
                    # Deduplicate products by direct_url to eliminate redundant listing rows
                    seen_urls: set[str] = set()
                    unique_products: list[EnrichedCommerceMatch] = []
                    for p in c.products:
                        if p.direct_url not in seen_urls:
                            seen_urls.add(p.direct_url)
                            unique_products.append(p)

                    # Display verified products with detected pricing
                    display_items = [p for p in unique_products if p.price is not None]
                    if not display_items:
                        # Fallback to unique product candidates or top items if no pricing was detected
                        display_items = unique_products[:15] if unique_products else c.items[:15]

                    table_title = (
                        "Commercial Products & Pricing"
                        if any(p.price for p in display_items)
                        else "Enriched Visual Matches"
                    )
                    console.print(_build_commerce_table(table_title, display_items))

                    articles_count = len(c.articles)
                    social_count = len(c.social)
                    other_count = len(c.items) - len(c.products) - articles_count - social_count
                    console.print(
                        f"[dim]ℹ Breakdown: {len(c.products)} commercial products, {articles_count} articles/editorial, "
                        f"{social_count} social media, {other_count} other pages. "
                        f"Run with --export-json to export all structured items.[/dim]"
                    )

            if export_csv:
                console.print(
                    "[yellow]⚠️ Note: CSV export is deprecated due to polymorphic Lens data; use --export-json for full structured intelligence.[/yellow]"
                )
                csv_path = _pro.export_commerce_to_csv(c, export_csv)
                if c.is_preview:
                    console.print(
                        f"[yellow]⚠️ Preview Mode: Exported 1 teaser listing to {csv_path}. Activate Pro (`google-lens activate`) to export all {len(results.visual_matches)} listings.[/yellow]"
                    )
                else:
                    console.print(f"[bold green]✓ Exported listings to:[/bold green] {csv_path}")

            if export_json:
                json_path = _pro.export_commerce_to_json(c, export_json)
                if c.is_preview:
                    console.print(
                        f"[yellow]⚠️ Preview Mode: Exported 1 teaser listing to {json_path}. Activate Pro (`google-lens activate`) to export all {len(results.visual_matches)} listings.[/yellow]"
                    )
                else:
                    console.print(
                        f"[bold green]✓ Exported all {len(c.items)} structured commerce listings to:[/bold green] {json_path}"
                    )

        else:
            # 3. Standard / Un-enriched Search Mode
            if results.analysis:
                console.print(_build_executive_panel(results))
            else:
                if results.ocr_text:
                    console.print("\n[bold green]Detected OCR Text:[/bold green]")
                    console.print(f"[dim]{results.ocr_text}[/dim]")

                if results.detected_objects:
                    console.print(
                        f"\n[bold green]Detected Objects/Regions:[/bold green] {len(results.detected_objects)}"
                    )
                    for obj in results.detected_objects:
                        bounds = (
                            f"cx={obj.bounding_box.center_x:.2f}, cy={obj.bounding_box.center_y:.2f}"
                            if obj.bounding_box
                            else "N/A"
                        )
                        console.print(f"  • [cyan]{obj.id}[/cyan] ({bounds})")

                if results.knowledge_graph and results.knowledge_graph.title:
                    console.print(
                        f"\n[bold yellow]Identified Entity:[/bold yellow] {results.knowledge_graph.title}"
                    )

            matches = results.visual_matches
            console.print(f"\n[bold green]Visual Matches Found:[/bold green] {len(matches)}")

            if matches:
                table = Table(title="Google Lens Visual Matches")
                table.add_column("#", style="cyan", width=4)
                table.add_column("Title", style="bold white", max_width=40)
                table.add_column("Source", style="green", width=16)
                table.add_column("Price", style="yellow", width=10)
                table.add_column("Destination URL", style="blue", overflow="fold")

                for idx, item in enumerate(matches[:20], 1):
                    link_str = f"[link={item.link}]{item.link}[/link]" if item.link else ""
                    table.add_row(
                        str(idx),
                        item.title[:40],
                        (item.source or "")[:16],
                        item.price or "",
                        link_str,
                    )

                console.print(table)
            else:
                console.print(
                    "[yellow]No external visual matches found on this search result page.[/yellow]"
                )

            if not enrich:
                console.print(
                    "[dim]💡 Pro tip: Pass '--enrich' to unlock canonical product links, normalized price comparisons, and best-deal ranking.[/dim]"
                )

        # Display Nano Banana Pro Synthesized Studio Packshot
        if results.studio_asset:
            sa = results.studio_asset
            console.print(
                "\n[bold magenta]🎨 Nano Banana Pro — Synthesized 8K Studio Asset[/bold magenta]"
            )
            console.print(f"  • [bold green]Saved Image:[/bold green] {sa.image_path}")
            console.print(f"  • [cyan]Model:[/cyan] {sa.model}")
            console.print(f"  • [dim]Prompt:[/dim] {sa.prompt_used}")

        # Display Financial Cost & Usage Telemetry
        if results.cost:
            c_dict = results.cost
            cost_info = c_dict.get("cost_usd", {})
            tokens_info = c_dict.get("tokens", {})
            total_cost = cost_info.get("total", 0.0)
            what_if = cost_info.get("what_if_paid")
            tier = c_dict.get("billing_tier", "unknown")
            total_tokens = tokens_info.get("total", 0)
            prompt_tokens = tokens_info.get("prompt", 0)
            output_tokens = tokens_info.get("output", 0)
            calls_cnt = c_dict.get("calls_count", 1)

            label = "💰 Total AI Cost:" if tier in ("free", "paid") else "💰 Estimated AI Cost:"
            if tier == "free":
                tier_badge = f" [cyan](Free Tier • ${what_if:.5f} if paid)[/cyan]"
            elif tier == "paid":
                tier_badge = " [dim](Paid Tier)[/dim]"
            else:
                tier_badge = " [dim](List Price • $0.00 if Free Tier)[/dim]"

            console.print(
                f"\n[bold green]{label}[/bold green] [bold white]${total_cost:.5f} USD[/bold white]{tier_badge} "
                f"[dim]({calls_cnt} call{'s' if calls_cnt > 1 else ''} | {total_tokens:,} tokens: {prompt_tokens:,} prompt / {output_tokens:,} output)[/dim]"
            )

        if output:
            Path(output).write_text(results.to_json())
            console.print(f"\n[green]Saved full results to [bold]{output}[/bold][/green]")

    except LensRateLimitError as e:
        stderr_console.print(
            "\n[bold red]Google Rate Limit / Bot Challenge Triggered (HTTP 429)[/bold red]"
        )
        stderr_console.print(f"[dim]{e}[/dim]\n")
        stderr_console.print("[yellow]Action Required to Enable Visual Matches:[/yellow]")
        stderr_console.print(
            f"  [bold green]➜ Run '{PROG_NAME} login' once to establish an authenticated session.[/bold green]"
        )
        stderr_console.print(
            "  After authenticating once, visual matches will run completely headless.\n"
        )
        stderr_console.print("[dim]Other production options:[/dim]")
        stderr_console.print("  • Set LENS_STORAGE_STATE_JSON or LENS_COOKIES in your environment")
        stderr_console.print(
            f"  • Use a residential proxy: {PROG_NAME} <query> --proxy 'http://...'"
        )
        stderr_console.print(
            f"  • Fast OCR & objects only (no auth needed): {PROG_NAME} <query> --ocr-only\n"
        )
        sys.exit(1)
    except LensError as e:
        stderr_console.print(f"[bold red]Lens Scraper Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        stderr_console.print(f"[bold red]Unexpected Error:[/bold red] {e}")
        sys.exit(1)


def get_skill_source_path() -> Path:
    """Locates the bundled Google Lens Agent Skill source directory."""
    # 1. Try importlib.resources
    for pkg in ("google_lens_pro",):
        for sub in ("google-lens-pro", "google-lens"):
            try:
                ref = pkg_resources.files(pkg).joinpath("data", "skill", sub)
                p = Path(str(ref))
                if p.exists() and (p / "SKILL.md").exists():
                    return p
            except Exception:
                pass

    # 2. Local package directory relative to this file
    pkg_dir = Path(__file__).resolve().parent
    for sub in ("google-lens-pro", "google-lens"):
        local_skill = pkg_dir / "data" / "skill" / sub
        if local_skill.exists() and (local_skill / "SKILL.md").exists():
            return local_skill

    # 3. Development repository root (.agents/skills/google-lens-pro)
    for sub in ("google-lens-pro", "google-lens"):
        repo_skill = pkg_dir.parent.parent / ".agents" / "skills" / sub
        if repo_skill.exists() and (repo_skill / "SKILL.md").exists():
            return repo_skill

    raise FileNotFoundError("Google Lens Agent Skill data files could not be located.")


@cli.command(name="install-skill")
@click.option(
    "--dest",
    "-d",
    type=click.Path(),
    help="Custom destination directory for the skill (e.g. ./my-skills/)",
)
@click.option(
    "--global",
    "-g",
    "is_global",
    is_flag=True,
    help="Install globally to user home directory (~/.agents/skills/ or ~/.claude/skills/)",
)
@click.option(
    "--claude",
    is_flag=True,
    help="Target Claude Code directory (.claude/skills/ or ~/.claude/skills/)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing skill directory if present",
)
def install_skill_cmd(
    dest: str | None,
    is_global: bool,
    claude: bool,
    force: bool,
) -> None:
    """Install the Google Lens Pro Agent Skill for AI agents (VS Code, Claude Code, Cursor, Codex)."""
    try:
        source_dir = get_skill_source_path()
    except Exception as e:
        console.print(f"[bold red]Error locating skill template:[/bold red] {e}")
        sys.exit(1)

    skill_name = "google-lens-pro"
    if dest:
        dest_path = Path(dest).resolve()
        target_dir = dest_path / skill_name if dest_path.name != skill_name else dest_path
    else:
        base_folder = ".claude" if claude else ".agents"
        parent_dir = Path.home() if is_global else Path.cwd()
        target_dir = parent_dir / base_folder / "skills" / skill_name

    if target_dir.exists():
        if not force:
            console.print(
                f"[yellow]Target skill directory already exists at:[/yellow] {target_dir}\n"
                "[dim]Pass --force to overwrite.[/dim]"
            )
            sys.exit(1)
        shutil.rmtree(target_dir)

    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, target_dir)

    # Ensure bundled scripts are executable
    scripts_dir = target_dir / "scripts"
    if scripts_dir.exists():
        for script_file in scripts_dir.glob("*.py"):
            with contextlib.suppress(OSError):
                script_file.chmod(script_file.stat().st_mode | 0o111)

    console.print(
        f"[bold green]✓ Successfully installed google-lens-pro Agent Skill to:[/bold green] {target_dir}"
    )
    console.print(
        "[dim]Compatible with VS Code Copilot, Claude Code, Cursor, Codex, Gemini CLI, etc.[/dim]\n"
    )
    console.print("[bold cyan]Example Agent Triggers:[/bold cyan]")
    console.print('  • "Find where to buy the jacket in this image: https://..."')
    console.print('  • "Extract all text from receipt.png using Google Lens OCR"')
    console.print('  • "What kind of flower is in photo.jpg?"')


# ---------------------------------------------------------------------------
# License Management & Pro Commands
# ---------------------------------------------------------------------------


@cli.group(name="license")
def license_group() -> None:
    """Manage Polar.sh license keys for Google Lens Pro features."""


@cli.command(name="buy")
@click.argument("plan_arg", required=False)
@click.option(
    "--plan",
    type=click.Choice(["lifetime", "monthly", "annual"], case_sensitive=False),
    default="lifetime",
    help="Plan to purchase (lifetime, monthly, or annual). Default: lifetime",
)
@click.pass_context
def buy_cmd(ctx: click.Context, plan_arg: str | None = None, plan: str = "lifetime") -> None:
    """Open the Polar.sh checkout page in your default browser to purchase Pro."""
    chosen = (plan_arg or plan or "lifetime").lower()
    if chosen in ("pro", "license"):
        chosen = "lifetime"
    checkout_url = _pro.POLAR_LINKS.get(chosen, _pro.POLAR_LINKS["lifetime"])

    console.print(
        f"[bold cyan]Opening Polar.sh checkout for Google Lens Pro ({chosen})...[/bold cyan]"
    )
    console.print(f"Checkout URL: [underline blue]{checkout_url}[/underline blue]\n")
    webbrowser.open(checkout_url)

    try:
        console.print("[bold yellow]Waiting for checkout completion...[/bold yellow]")
        console.print(
            "[dim]Once checkout is complete on Polar, paste your license key below to activate immediately.[/dim]\n"
        )
        entered_key = click.prompt(
            "Enter Polar License Key (or press Enter to activate later)",
            default="",
            show_default=False,
        ).strip()
        if entered_key:
            console.print()
            ctx.invoke(activate_cmd, key=entered_key)
            return
    except (click.Abort, EOFError):
        pass

    console.print(
        "[green]After completing checkout, activate your license in terminal with:[/green]"
    )
    console.print(f"  [bold cyan]{PROG_NAME} pro activate <your-key>[/bold cyan]\n")


# Alias for buy
cli.add_command(buy_cmd, name="purchase")


@cli.command(name="activate")
@click.argument("key", required=False)
@click.option("--key", "-k", "key_opt", help="Polar.sh license key (LENS_...)")
def activate_cmd(key: str | None = None, key_opt: str | None = None) -> None:
    """Activate Google Lens Pro license on this machine."""
    _require_pro()
    license_key = (key or key_opt or "").strip()

    if not license_key:
        console.print("[bold cyan]✨ Google Lens Pro — License Activation[/bold cyan]\n")
        console.print("Don't have a license key yet? Purchase one on Polar:")
        console.print(
            f"  • [bold]Lifetime ($99)[/bold]: [underline blue]{_pro.POLAR_LINKS['lifetime']}[/underline blue]"
        )
        console.print(
            f"  • [bold]Monthly ($19/mo)[/bold]: [underline blue]{_pro.POLAR_LINKS['monthly']}[/underline blue]"
        )
        console.print(
            f"  • [bold]Annual ($99/yr)[/bold]:  [underline blue]{_pro.POLAR_LINKS['annual']}[/underline blue]\n"
        )

        if click.confirm("Open Polar checkout page in your browser?", default=False):
            webbrowser.open(_pro.POLAR_LINKS["lifetime"])
            console.print("[green]✓ Opened Polar checkout in your browser.[/green]\n")

        entered = click.prompt("Enter your Polar License Key (LENS_...)", hide_input=False)
        license_key = entered.strip()

    if not license_key:
        stderr_console.print("[bold red]✗ No license key provided.[/bold red]")
        sys.exit(1)

    console.print("[bold cyan]Activating Google Lens Pro license...[/bold cyan]")
    info = _pro.license_manager.activate(license_key)
    if info.is_valid:
        console.print("[bold green]✓ License activated successfully![/bold green]")
        if info.customer_email:
            console.print(f"  • Registered to: [cyan]{info.customer_email}[/cyan]")
        if info.expires_at:
            console.print(f"  • Expires at: [dim]{info.expires_at}[/dim]")
        console.print(f"  • Device label: [dim]{_pro.get_machine_label()}[/dim]")
        console.print("[bold green]Pro features unlocked on this machine.[/bold green]")
    else:
        stderr_console.print(
            f"[bold red]✗ License activation failed:[/bold red] {info.error_message}"
        )
        sys.exit(1)


@cli.command(name="setup-ai")
@click.option("--key", help="Google AI Studio Gemini API key")
@click.option(
    "--tier",
    type=click.Choice(["unknown", "free", "paid"], case_sensitive=False),
    help="Gemini billing tier: 'unknown' (dynamic list price), 'free' (AI Studio), or 'paid' (GCP Pay-as-you-go)",
)
@click.option("--status", is_flag=True, help="Display the current configured Gemini API key status")
def setup_ai_cmd(key: str | None, tier: str | None = None, status: bool = False) -> None:
    """Configure a Google AI Studio API key and billing tier for multimodal intelligence."""
    from .settings import (
        get_gemini_api_key,
        get_gemini_billing_tier,
        set_gemini_api_key,
        set_gemini_billing_tier,
    )

    def _mask(k: str) -> str:
        return k[:6] + "..." + k[-4:]

    def _tier_label(t: str) -> str:
        if t == "unknown":
            return "UNKNOWN (Calculated at standard Google Cloud list rates)"
        return t.upper()

    current = get_gemini_api_key()
    current_tier = get_gemini_billing_tier()

    if status:
        if current:
            console.print(f"Current Gemini API key: [cyan]{_mask(current)}[/cyan]")
        else:
            console.print("[dim]No Gemini API key currently configured.[/dim]")
        console.print(f"Billing tier: [yellow]{_tier_label(current_tier)}[/yellow]")
        return

    if tier:
        set_gemini_billing_tier(tier)
        console.print(f"[bold green]✓ Set Gemini billing tier to '{tier}'.[/bold green]")

    if key:
        set_gemini_api_key(key)
        console.print("[bold green]✓ Saved Gemini API key to local config.[/bold green]")

    if not key and not tier:
        if current:
            console.print(f"Current Gemini API key: [cyan]{_mask(current)}[/cyan]")
            console.print(f"Billing tier: [yellow]{_tier_label(current_tier)}[/yellow]")

        console.print(
            "Get a free Google AI Studio key at: [underline blue]https://aistudio.google.com/app/apikey[/underline blue]"
        )
        entered = click.prompt(
            "Enter new Gemini API key (or leave empty to keep current)", default="", hide_input=True
        )
        if entered and entered.strip():
            set_gemini_api_key(entered.strip())
            console.print("[bold green]✓ Gemini API key updated successfully.[/bold green]")


@license_group.command(name="buy")
@click.argument("plan_arg", required=False)
@click.option(
    "--plan",
    type=click.Choice(["lifetime", "monthly", "annual"], case_sensitive=False),
    default="lifetime",
    help="Plan to purchase (lifetime, monthly, or annual). Default: lifetime",
)
@click.pass_context
def buy_license_cmd(
    ctx: click.Context, plan_arg: str | None = None, plan: str = "lifetime"
) -> None:
    """Open the Polar.sh checkout page to purchase a Pro license."""
    ctx.invoke(buy_cmd, plan_arg=plan_arg, plan=plan)


license_group.add_command(buy_license_cmd, name="purchase")


@license_group.command(name="activate")
@click.argument("license_key", required=False)
@click.pass_context
def activate_license_cmd(ctx: click.Context, license_key: str | None) -> None:
    """Activate a Polar.sh license key on this machine."""
    ctx.invoke(activate_cmd, key=license_key)


@license_group.command(name="status")
def status_license_cmd() -> None:
    """Check the status of the local Google Lens Pro license."""
    _require_pro()
    info = _pro.license_manager.validate()
    table = Table(title="Google Lens Pro License Status")
    table.add_column("Property", style="bold cyan")
    table.add_column("Value", style="white")

    table.add_row(
        "Status",
        "[bold green]Active (Pro Unlocked)[/bold green]"
        if info.is_valid
        else "[bold red]Inactive / Locked[/bold red]",
    )
    table.add_row(
        "License Key",
        info.key[:10] + "..." + info.key[-4:]
        if len(info.key) > 14
        else (info.key or "[dim]Not configured[/dim]"),
    )
    if info.customer_email:
        table.add_row("Customer Email", info.customer_email)
    if info.expires_at:
        table.add_row("Expires At", info.expires_at)
    table.add_row("Device Label", _pro.get_machine_label())

    console.print(table)
    if not info.is_valid:
        console.print()
        console.print(Markdown(_pro.get_paywall_message()))


@license_group.command(name="deactivate")
def deactivate_license_cmd() -> None:
    """Deactivate the license on this device and clear local cache."""
    _require_pro()
    _pro.license_manager.deactivate()
    console.print("[bold yellow]✓ License deactivated and local cache cleared.[/bold yellow]")


@cli.group(name="pro", invoke_without_command=True)
@click.pass_context
def pro_group(ctx: click.Context) -> None:
    """Google Lens Pro — Commercial intelligence, arbitrage & activations."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(status_license_cmd)


pro_group.add_command(buy_license_cmd, name="buy")
pro_group.add_command(buy_license_cmd, name="purchase")
pro_group.add_command(activate_license_cmd, name="activate")
pro_group.add_command(status_license_cmd, name="status")
pro_group.add_command(deactivate_license_cmd, name="deactivate")


@cli.command(name="upgrade")
@click.option(
    "--open-browser/--no-open-browser",
    default=True,
    help="Open Polar checkout link in default web browser",
)
def upgrade_cmd(open_browser: bool) -> None:
    """View Google Lens Pro plans and open Polar checkout."""
    console.print(
        Panel(
            "[bold cyan]Google Lens Pro — Pricing & Plans[/bold cyan]\n\n"
            "• [bold]Monthly[/bold] ($19/mo): Full pricing analytics, canonical URLs, and merchant categorization\n"
            "• [bold]Annual[/bold] ($99/yr): Save 55% + priority selector updates\n"
            "• [bold]Lifetime[/bold] ($99 Launch Special): Single payment, unlocked forever across 3 devices\n\n"
            f"Monthly Checkout:  [underline blue]{_pro.POLAR_LINKS['monthly']}[/underline blue]\n"
            f"Annual Checkout:   [underline blue]{_pro.POLAR_LINKS['annual']}[/underline blue]\n"
            f"Lifetime Checkout: [underline blue]{_pro.POLAR_LINKS['lifetime']}[/underline blue]",
            title="✨ Unlock Google Lens Pro",
            border_style="magenta",
        )
    )
    if open_browser:
        with contextlib.suppress(Exception):
            click.launch(_pro.POLAR_LINKS["lifetime"])


def main() -> None:
    """Entrypoint for pyproject.toml console script."""
    cli()


if __name__ == "__main__":
    main()
