from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from .config import JiraSettings, load_settings
from .jira import JiraClient, JiraError
from .markdown import discover_tickets
from .models import Action, PlanItem
from .planner import build_plan, validate_ticket_set
from .sync import execute_plan

app = typer.Typer(no_args_is_help=True, help="Synchronize Markdown tickets with Jira Cloud.")
console = Console()


def _resolve_path(path: Path | None, settings: JiraSettings) -> Path:
    return path or Path(settings.ticket_directory)


def _client(settings: JiraSettings) -> JiraClient:
    missing = [
        name for name, value in {
            "JIRA_BASE_URL": settings.base_url,
            "JIRA_EMAIL": settings.email,
            "JIRA_API_TOKEN": settings.api_token,
        }.items() if not value
    ]
    if missing:
        raise typer.BadParameter("Missing Jira configuration: " + ", ".join(missing))
    return JiraClient(settings.base_url, settings.email, settings.api_token)  # type: ignore[arg-type]


def _load(path: Path | None):
    settings = load_settings(path or Path.cwd())
    ticket_path = _resolve_path(path, settings)
    tickets = discover_tickets(ticket_path, default_project=settings.project)
    if not tickets:
        raise typer.BadParameter(f"No Markdown tickets found in {ticket_path}")
    return settings, ticket_path, tickets


def _plan_payload(items: list[PlanItem], ticket_path: Path, *, offline: bool) -> dict[str, object]:
    root = ticket_path if ticket_path.is_dir() else ticket_path.parent
    counts = {action.value.lower(): 0 for action in Action}
    rendered_items: list[dict[str, object]] = []
    for item in items:
        counts[item.action.value.lower()] += 1
        try:
            path = str(item.ticket.path.relative_to(root))
        except ValueError:
            path = str(item.ticket.path)
        rendered_items.append(
            {
                "action": item.action.value,
                "file": path,
                "local_id": item.ticket.local_id,
                "jira_key": item.ticket.jira_key,
                "project": item.ticket.project,
                "issue_type": item.ticket.issue_type,
                "summary": item.ticket.summary,
                "parent": item.ticket.parent,
                "resolved_parent_key": item.resolved_parent,
                "priority": item.ticket.priority,
                "labels": item.ticket.labels,
                "reason": item.reason,
            }
        )
    return {
        "schema_version": 1,
        "mode": "offline" if offline else "online",
        "summary": {"total": len(items), **counts},
        "items": rendered_items,
    }


@app.command()
def validate(
    path: Annotated[Path | None, typer.Argument(help="Markdown ticket file or directory")] = None,
) -> None:
    """Validate local Markdown tickets without contacting Jira."""
    _, _, tickets = _load(path)
    errors = validate_ticket_set(tickets)
    if errors:
        for error in errors:
            console.print(f"[red]ERROR[/red] {error}")
        raise typer.Exit(code=1)
    console.print(f"[green]Valid[/green]: {len(tickets)} ticket(s)")


@app.command()
def plan(
    path: Annotated[Path | None, typer.Argument(help="Markdown ticket file or directory")] = None,
    offline: Annotated[bool, typer.Option("--offline", help="Do not contact Jira; infer update/create from jira_key only")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Emit a machine-readable JSON plan")] = False,
) -> None:
    """Show what would be created or updated."""
    settings, ticket_path, tickets = _load(path)
    try:
        if offline:
            items = build_plan(tickets)
        else:
            with _client(settings) as jira:
                items = build_plan(tickets, jira)
    except (ValueError, JiraError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    if json_output:
        typer.echo(json.dumps(_plan_payload(items, ticket_path, offline=offline), indent=2, ensure_ascii=False))
        return

    table = Table(title="jira-sync plan")
    table.add_column("Action")
    table.add_column("File")
    table.add_column("Type")
    table.add_column("Summary")
    table.add_column("Parent")
    table.add_column("Reason")
    for item in items:
        table.add_row(
            item.action.value,
            str(item.ticket.path),
            item.ticket.issue_type,
            item.ticket.summary,
            item.ticket.parent or "",
            item.reason,
        )
    console.print(table)


@app.command()
def push(
    path: Annotated[Path | None, typer.Argument(help="Markdown ticket file or directory")] = None,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt")] = False,
    no_write_back: Annotated[bool, typer.Option("--no-write-back", help="Do not add jira_key to created ticket files")] = False,
) -> None:
    """Create/update Jira issues and write created keys back to Markdown."""
    settings, _, tickets = _load(path)
    try:
        with _client(settings) as jira:
            items = build_plan(tickets, jira)
            creates = sum(i.action.value == "CREATE" for i in items)
            updates = sum(i.action.value == "UPDATE" for i in items)
            console.print(f"Plan: [green]{creates} create[/green], [yellow]{updates} update[/yellow]")
            if not yes and not typer.confirm("Apply this plan to Jira?"):
                raise typer.Abort()
            results = execute_plan(items, jira, write_back=not no_write_back)
    except (ValueError, JiraError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    for item, key in results:
        console.print(f"[green]{item.action.value}[/green] {key}  {item.ticket.summary}")


if __name__ == "__main__":
    app()
