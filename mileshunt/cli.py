"""MilesHunt CLI — Flying Blue XP deal finder."""

from __future__ import annotations

from datetime import datetime, timedelta

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from mileshunt.search import FlightDeal, hunt, search_route
from mileshunt.skyteam import AIRLINE_NAMES, DEST_GROUPS

app = typer.Typer(
    name="mileshunt",
    help="Flying Blue XP optimizer — find the cheapest SkyTeam deals by $/XP.",
    no_args_is_help=True,
)
console = Console()


def _tomorrow() -> str:
    return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")


def _rating_style(rating: str) -> str:
    return {"EXCELLENT": "bold green", "GOOD": "yellow", "OK": "dark_orange", "EXPENSIVE": "red"}.get(rating, "white")


def _print_results(deals: list[FlightDeal], limit: int = 30) -> None:
    if not deals:
        console.print("[dim]No flights with FB-earning XP found.[/dim]")
        return

    table = Table(title="Results — sorted by $/XP", show_lines=False, padding=(0, 1))
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Route", min_width=20)
    table.add_column("Price", justify="right", style="cyan")
    table.add_column("XP", justify="right", style="bold yellow")
    table.add_column("RT XP", justify="right", style="yellow")
    table.add_column("$/XP", justify="right")
    table.add_column("Seg", justify="center")
    table.add_column("Airlines")
    table.add_column("Rating")

    for i, d in enumerate(deals[:limit], 1):
        rating_text = Text(d.rating, style=_rating_style(d.rating))
        airlines = ", ".join(d.airline_names)
        table.add_row(
            str(i),
            d.route,
            f"${d.price:,.0f}",
            str(d.xp),
            str(d.xp_rt),
            f"${d.per_xp}",
            str(d.segments),
            airlines,
            rating_text,
        )

    console.print(table)

    # Summary
    best = deals[0]
    multi = [d for d in deals if d.segments >= 3]
    console.print()
    console.print(f"[bold]Total deals:[/bold]  {len(deals)}")
    console.print(f"[bold]Best $/XP:[/bold]    ${best.per_xp}/XP — {best.route} at ${best.price:,.0f}")
    if multi:
        bm = min(multi, key=lambda d: d.per_xp)
        console.print(f"[bold]Best multi:[/bold]   ${bm.per_xp}/XP — {bm.route} ({bm.xp} XP, ${bm.price:,.0f})")


@app.command()
def search(
    origin: str = typer.Argument(..., help="Origin airport IATA code (e.g. AMS)"),
    dest: str = typer.Argument(..., help="Destination airport IATA code (e.g. NCE)"),
    date: str = typer.Argument(None, help="Date YYYY-MM-DD (default: tomorrow)"),
    cabin: str = typer.Option("business", "--cabin", "-c", help="Cabin: economy/premium/business/first"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max results to show"),
):
    """Search a specific route for best XP deals."""
    date = date or _tomorrow()
    origin = origin.upper()
    dest = dest.upper()

    console.print(f"\n[bold]Searching[/bold] {origin} > {dest}  |  {date}  |  {cabin}\n")

    with console.status(f"Searching {origin} > {dest}..."):
        deals = search_route(origin, dest, date, cabin)

    _print_results(deals, limit)


@app.command(name="hunt")
def hunt_cmd(
    date: str = typer.Argument(None, help="Date YYYY-MM-DD (default: tomorrow)"),
    origin: str = typer.Option("AMS", "--origin", "-o", help="Origin airport"),
    groups: str = typer.Option(None, "--groups", "-g", help="Comma-separated group IDs (default: all default-on)"),
    cabin: str = typer.Option("business", "--cabin", "-c", help="Cabin: economy/premium/business/first"),
    limit: int = typer.Option(30, "--limit", "-n", help="Max results to show"),
):
    """Hunt across destination groups for the best XP deals."""
    date = date or _tomorrow()
    group_ids = [g.strip() for g in groups.split(",")] if groups else None

    # Show config
    active_groups = (
        [g for g in DEST_GROUPS if g.id in group_ids] if group_ids
        else [g for g in DEST_GROUPS if g.default_on]
    )
    group_labels = ", ".join(g.label for g in active_groups)
    dest_count = len(set(d for g in active_groups for d in g.destinations if d != origin))

    console.print()
    console.print("[bold cyan]MilesHunt — XP Hunter[/bold cyan]")
    console.print(f"  Date:     {date}")
    console.print(f"  Origin:   {origin}")
    console.print(f"  Cabin:    {cabin}")
    console.print(f"  Groups:   {group_labels}")
    console.print(f"  Routes:   {dest_count} destinations")
    console.print()

    def on_progress(label: str, current: int, total: int):
        console.print(f"  [{current}/{total}] {label}", highlight=False)

    deals = hunt(date, origin, group_ids, cabin, on_progress=on_progress)

    console.print()
    _print_results(deals, limit)


@app.command(name="groups")
def list_groups():
    """List all available destination groups."""
    table = Table(title="Destination Groups")
    table.add_column("ID", style="cyan")
    table.add_column("Label", style="bold")
    table.add_column("Default", justify="center")
    table.add_column("Destinations", style="dim")
    table.add_column("Description")

    for g in DEST_GROUPS:
        table.add_row(
            g.id,
            g.label,
            "ON" if g.default_on else "",
            f"{len(g.destinations)} cities",
            g.description,
        )

    console.print(table)


@app.command(name="xp")
def xp_table():
    """Show the Flying Blue XP reference table."""
    from mileshunt.xp import BAND_LABELS, XP_TABLE

    table = Table(title="Flying Blue XP per Segment")
    table.add_column("Band", style="bold")
    table.add_column("Economy", justify="right")
    table.add_column("Premium", justify="right")
    table.add_column("Business", justify="right", style="bold yellow")
    table.add_column("First", justify="right")

    for band_key, label in BAND_LABELS.items():
        row = XP_TABLE[band_key]
        table.add_row(label, str(row["economy"]), str(row["premium"]), str(row["business"]), str(row["first"]))

    console.print(table)
    console.print("\n[dim]XP is earned per segment. Business = 15 XP per European leg. More stops = more XP.[/dim]")


if __name__ == "__main__":
    app()
