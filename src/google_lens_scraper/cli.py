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
from .client import LensScraper
from .config import LensConfig
from .exceptions import LensError, LensRateLimitError
from .models import EnrichedCommerceMatch
from .parser import PROG_NAME
from .session import SessionManager

console = Console()
stderr_console = Console(stderr=True)


def _require_pro() -> None:
    """Stops a Pro-only command cleanly when the Pro engines are not installed."""
    if not _pro.AVAILABLE:
        raise click.ClickException(
            "Google Lens Pro engines are not part of the MIT source tree. "
            "Install the published package instead: pip install google-lens-scraper"
        )


def _build_commerce_table(title: str, items: list[EnrichedCommerceMatch]) -> Table:
    """Builds the shared Rich table layout used for both preview and full commerce listings."""
    table = Table(title=title)
    table.add_column("Score", style="bold green", justify="right", width=6)
    table.add_column("Type", style="bold cyan", width=12)
    table.add_column("Brand", style="yellow", width=12)
    table.add_column("SKU", style="dim", width=12)
    table.add_column("Title", style="bold white", max_width=30)
    table.add_column("Price", style="bold green", width=12)
    table.add_column("Stock", style="magenta", width=12)
    table.add_column("Condition", style="blue", width=10)
    table.add_column("Merchant", style="cyan", width=14)
    table.add_column("Clean URL", style="blue", max_width=40)

    for item in items:
        price_str = f"{item.price.amount:.2f} {item.price.currency}" if item.price else "N/A"
        stock_str = item.stock_status.value if item.stock_status else "N/A"
        cond_str = item.condition.value if item.condition else "N/A"
        table.add_row(
            f"{item.match_score}%",
            item.page_type.value,
            item.brand or "N/A",
            item.sku or "N/A",
            item.title[:30],
            price_str,
            stock_str,
            cond_str,
            item.merchant_name or "N/A",
            item.direct_url[:40],
        )
    return table


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

        # Otherwise, assume it's the image QUERY argument for 'search'
        return "search", self.get_command(ctx, "search"), args


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
@click.option("--timeout", default=30.0, help="Request timeout in seconds")
def search_cmd(
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
    timeout: float,
) -> None:
    """Search Google Lens for visual matches, OCR text, and entities.

    QUERY can be a public image URL, local image file path, or a Google Lens search URL.
    """
    config = LensConfig(
        headless=headless,
        timeout=timeout,
        cookies=cookies,
        proxy=proxy,
        user_data_dir=profile_dir,
        cdp_url=cdp_url,
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

        # Display OCR text if present
        if results.ocr_text:
            console.print("\n[bold green]Detected OCR Text:[/bold green]")
            console.print(f"[dim]{results.ocr_text}[/dim]")

        # Display Detected Objects
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

        # Display Knowledge Graph if present
        if results.knowledge_graph and results.knowledge_graph.title:
            console.print(
                f"\n[bold yellow]Identified Entity:[/bold yellow] {results.knowledge_graph.title}"
            )

        # Display Visual Matches Table if in full mode
        if not ocr_only:
            matches = results.visual_matches
            console.print(f"\n[bold green]Visual Matches Found:[/bold green] {len(matches)}")

            if matches:
                table = Table(title="Google Lens Visual Matches")
                table.add_column("#", style="cyan", width=4)
                table.add_column("Title", style="bold white", max_width=40)
                table.add_column("Source", style="green", width=16)
                table.add_column("Price", style="yellow", width=10)
                table.add_column("Destination URL", style="blue", max_width=50)

                for idx, item in enumerate(matches[:20], 1):
                    table.add_row(
                        str(idx),
                        item.title[:40],
                        (item.source or "")[:16],
                        item.price or "",
                        item.link[:50],
                    )

                console.print(table)
            else:
                console.print(
                    "[yellow]No external visual matches found on this search result page.[/yellow]"
                )

        # Display Pro Commerce Intelligence if requested
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
                # Full Pro Output
                s = c.summary
                console.print(
                    "\n[bold magenta]✨ Google Lens Pro — Resale & Pricing Intelligence[/bold magenta]"
                )
                sum_table = Table(title="Market Pricing Analytics")
                sum_table.add_column("Metric", style="bold cyan")
                sum_table.add_column("Value", style="bold white")
                sum_table.add_row("Total Analyzed Listings", str(s.total_matches))
                sum_table.add_row("Priced Listings", str(s.total_priced_matches))
                if s.min_price is not None:
                    sum_table.add_row("Lowest Market Price", f"{s.min_price:.2f} {s.currency}")
                if s.max_price is not None:
                    sum_table.add_row("Highest Market Price", f"{s.max_price:.2f} {s.currency}")
                if s.avg_price is not None:
                    sum_table.add_row("Average Market Price", f"{s.avg_price:.2f} {s.currency}")
                if s.best_deal:
                    sum_table.add_row(
                        "🏆 Best Deal Seller",
                        f"{s.best_deal.merchant_name} ({s.best_deal.price.amount if s.best_deal.price else 'N/A'} {s.currency})\n[blue]{s.best_deal.direct_url}[/blue]",
                    )
                console.print(sum_table)

                if c.items:
                    products = c.products
                    display_items = products if products else c.items[:15]
                    table_title = (
                        "Commercial Products & Pricing" if products else "Enriched Visual Matches"
                    )
                    console.print(_build_commerce_table(table_title, display_items))

                    articles_count = len(c.articles)
                    social_count = len(c.social)
                    other_count = len(c.items) - len(products) - articles_count - social_count
                    console.print(
                        f"[dim]ℹ Breakdown: {len(products)} commercial products, {articles_count} articles/editorial, "
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

        elif not enrich and not json_output:
            console.print(
                "[dim]💡 Pro tip: Pass '--enrich' to unlock canonical product links, normalized price comparisons, and best-deal ranking.[/dim]"
            )

        # Display Deep Multimodal Product Intelligence
        if results.analysis:
            a = results.analysis
            console.print(
                "\n[bold cyan]🧠 Gemini 3.8 Flash — Multimodal Visual Intelligence[/bold cyan]"
            )
            if a.summary:
                console.print(f"[italic]{a.summary}[/italic]\n")

            attr_table = Table(title="Identified Product Attributes")
            attr_table.add_column("Attribute", style="bold cyan", width=22)
            attr_table.add_column("Value", style="bold white")

            attrs = a.attributes
            if attrs.brand:
                attr_table.add_row("Brand", attrs.brand)
            if attrs.model_or_name:
                attr_table.add_row("Model / Silhouette", attrs.model_or_name)
            if attrs.category:
                attr_table.add_row("Category", attrs.category)
            if attrs.color:
                attr_table.add_row("Colorway", attrs.color)
            if attrs.materials:
                attr_table.add_row("Materials", ", ".join(attrs.materials))
            if attrs.condition_assessment:
                attr_table.add_row("Condition Assessment", attrs.condition_assessment)
            if attrs.key_features:
                attr_table.add_row("Key Features", " • ".join(attrs.key_features))
            if attrs.authenticity_markers:
                attr_table.add_row("Authenticity Markers", " • ".join(attrs.authenticity_markers))
            if attrs.estimated_msrp_usd is not None:
                attr_table.add_row("Estimated MSRP", f"${attrs.estimated_msrp_usd:,.2f} USD")
            attr_table.add_row("Confidence", f"{attrs.confidence_score * 100:.1f}%")

            console.print(attr_table)

            if a.resale_recommendation:
                console.print(
                    f"\n[bold yellow]Resale Outlook:[/bold yellow] {a.resale_recommendation}"
                )
            if a.tags:
                console.print(f"[dim]Tags: {', '.join(a.tags)}[/dim]")

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
            total_tokens = tokens_info.get("total", 0)
            prompt_tokens = tokens_info.get("prompt", 0)
            output_tokens = tokens_info.get("output", 0)
            calls_cnt = c_dict.get("calls_count", 1)

            console.print(
                f"\n[bold green]💰 Total AI Cost:[/bold green] [bold white]${total_cost:.5f} USD[/bold white] "
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
    try:
        ref = pkg_resources.files("google_lens_scraper").joinpath("data", "skill", "google-lens")
        p = Path(str(ref))
        if p.exists() and (p / "SKILL.md").exists():
            return p
    except Exception:
        pass

    # 2. Local package directory relative to this file
    pkg_dir = Path(__file__).resolve().parent
    local_skill = pkg_dir / "data" / "skill" / "google-lens"
    if local_skill.exists() and (local_skill / "SKILL.md").exists():
        return local_skill

    # 3. Development repository root (.agents/skills/google-lens)
    repo_skill = pkg_dir.parent.parent / ".agents" / "skills" / "google-lens"
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
    """Install the Google Lens Agent Skill for AI agents (VS Code, Claude Code, Cursor, Codex)."""
    try:
        source_dir = get_skill_source_path()
    except Exception as e:
        console.print(f"[bold red]Error locating skill template:[/bold red] {e}")
        sys.exit(1)

    if dest:
        dest_path = Path(dest).resolve()
        target_dir = dest_path / "google-lens" if dest_path.name != "google-lens" else dest_path
    else:
        base_folder = ".claude" if claude else ".agents"
        parent_dir = Path.home() if is_global else Path.cwd()
        target_dir = parent_dir / base_folder / "skills" / "google-lens"

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
        f"[bold green]✓ Successfully installed google-lens Agent Skill to:[/bold green] {target_dir}"
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
@click.option("--status", is_flag=True, help="Display the current configured Gemini API key status")
def setup_ai_cmd(key: str | None, status: bool = False) -> None:
    """Configure a Google AI Studio API key for Nano Banana Pro 8K packshots."""
    from .settings import get_gemini_api_key, set_gemini_api_key

    current = get_gemini_api_key()
    if status:
        if current:
            masked = current[:6] + "..." + current[-4:]
            console.print(f"Current Gemini API key: [cyan]{masked}[/cyan]")
        else:
            console.print("[dim]No Gemini API key currently configured.[/dim]")
        return

    if key:
        set_gemini_api_key(key)
        console.print("[bold green]✓ Saved Gemini API key to local config.[/bold green]")
        return

    if current:
        masked = current[:6] + "..." + current[-4:]
        console.print(f"Current Gemini API key: [cyan]{masked}[/cyan]")

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
