"""TokenWatch CLI — tw command."""

import click
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

from ..storage import Storage, DEFAULT_DB_PATH


console = Console()


def get_storage() -> Storage:
    """Get storage instance, using TOKENWATCH_DB env var if set."""
    import os
    db_path_str = os.environ.get("TOKENWATCH_DB")
    if db_path_str:
        return Storage(db_path=Path(db_path_str))
    return Storage()


def parse_period(period: str) -> datetime:
    """Parse a period string like '7d', '30d', 'today' into a start datetime."""
    now = datetime.now(UTC)
    if period == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period.endswith("d"):
        days = int(period[:-1])
        return now - timedelta(days=days)
    if period.endswith("h"):
        hours = int(period[:-1])
        return now - timedelta(hours=hours)
    raise click.BadParameter(f"Invalid period: {period}. Use 'today', '7d', '30d', etc.")


@click.group()
def main():
    """TokenWatch — htop for LLM spend."""
    pass


@main.command()
@click.option("--period", default=None, help="Time period (e.g., today, 7d, 30d)")
def report(period: Optional[str]):
    """Show spending summary."""
    storage = get_storage()

    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Show today, 7d, 30d summaries
    periods = {
        "Today": today_start,
        "Last 7 days": now - timedelta(days=7),
        "Last 30 days": now - timedelta(days=30),
    }

    if period:
        period_start = parse_period(period)
        periods = {period: period_start}

    has_data = False

    for label, start in periods.items():
        total = storage.get_total_cost(start, now)
        if total > 0:
            has_data = True

        models = storage.get_summary_by_model(start, now)

        console.print(f"\n[bold]{label}[/bold]: [green]${total:.2f}[/green]")

        if models:
            table = Table(show_header=True, header_style="bold dim")
            table.add_column("Model")
            table.add_column("Cost", justify="right")
            table.add_column("Requests", justify="right")
            table.add_column("Tokens", justify="right")

            for m in models:
                pct = (m["total_cost"] / total * 100) if total > 0 else 0
                table.add_row(
                    m["model"],
                    f"${m['total_cost']:.2f} ({pct:.0f}%)",
                    str(m["request_count"]),
                    f"{m['total_input'] + m['total_output']:,}",
                )
            console.print(table)

    if not has_data:
        console.print("\n[dim]No usage data recorded yet.[/dim]")
        console.print("[dim]Wrap your OpenAI client with TokenWatch to start tracking:[/dim]")
        console.print("[dim]  from tokenwatch import TokenWatch[/dim]")
        console.print("[dim]  tw = TokenWatch()[/dim]")
        console.print("[dim]  client = tw.wrap(openai.OpenAI())[/dim]")


@main.command()
@click.option("--by", "dimension", required=True, type=click.Choice(["model", "caller"]),
              help="Dimension to group by")
@click.option("--period", default="7d", help="Time period (default: 7d)")
@click.option("--limit", default=10, help="Number of results to show")
def top(dimension: str, period: str, limit: int):
    """Show top spenders by dimension."""
    storage = get_storage()
    now = datetime.now(UTC)
    start = parse_period(period)

    if dimension == "model":
        results = storage.get_summary_by_model(start, now)
    elif dimension == "caller":
        results = storage.get_summary_by_caller(start, now)
    else:
        console.print(f"[red]Unknown dimension: {dimension}[/red]")
        return

    results = results[:limit]

    if not results:
        console.print("[dim]No data for this period.[/dim]")
        return

    table = Table(title=f"Top by {dimension} ({period})", show_header=True, header_style="bold")
    table.add_column(dimension.capitalize())
    table.add_column("Cost", justify="right")
    table.add_column("Requests", justify="right")
    table.add_column("Avg Tokens/Req", justify="right")

    for r in results:
        key = r.get(dimension, "unknown")
        total_tokens = r["total_input"] + r["total_output"]
        avg_tokens = total_tokens // r["request_count"] if r["request_count"] > 0 else 0
        table.add_row(
            str(key),
            f"${r['total_cost']:.4f}",
            str(r["request_count"]),
            f"{avg_tokens:,}",
        )

    console.print(table)


@main.command()
@click.option("--days", default=7, help="Number of days to show (default: 7)")
def trend(days: int):
    """Show daily spending trend as an ASCII chart."""
    storage = get_storage()
    now = datetime.now(UTC)
    start = now - timedelta(days=days)

    daily_costs = storage.get_daily_costs(start, now)

    if not daily_costs:
        console.print("[dim]No usage data for this period.[/dim]")
        return

    # Build a dict of day -> cost
    cost_by_day: dict[str, float] = {}
    for row in daily_costs:
        cost_by_day[row["day"]] = row["total_cost"]

    # Generate all days in range
    all_days: list[str] = []
    for i in range(days):
        day = (now - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        all_days.append(day)

    values = [cost_by_day.get(day, 0.0) for day in all_days]
    max_val = max(values) if values else 0.0

    console.print(f"\n[bold]Daily spend (last {days} days)[/bold]\n")

    chart_width = 40
    for day, val in zip(all_days, values):
        bar_len = int((val / max_val) * chart_width) if max_val > 0 else 0
        bar = "\u2588" * bar_len
        short_day = day[5:]  # MM-DD
        console.print(f"  {short_day} | {bar} ${val:.4f}")

    total = sum(values)
    console.print(f"\n  [bold]Total:[/bold] [green]${total:.4f}[/green]")
