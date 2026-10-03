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


def _relative_ticket_path(path: Path, ticket_path: Path) -> str:
    root = ticket_path if ticket_path.is_dir() else ticket_path.parent
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _action_summary(items: list[PlanItem]) -> dict[str, int]:
    counts = {action.value.lower(): 0 for action in Action}
    for item in items:
        counts[item.action.value.lower()] += 1
    return {"total": len(items), **counts}


def _plan_payload(items: list[PlanItem], ticket_path: Path, *, offline: bool) -> dict[str, object]:
    rendered_items: list[dict[str, object]] = []
    for item in items:
        rendered_items.append(
            {
                "action": item.action.value,
                "file": _relative_ticket_path(item.ticket.path, ticket_path),
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
                "changed_fields": item.changed_fields,
            }
        )
    return {
        "schema_version": 1,
        "mode": "offline" if offline else "online",
        "summary": _action_summary(items),
        "items": rendered_items,
    }


def _validation_payload(ticket_count: int, errors: list[str]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "valid": not errors,
        "summary": {"tickets": ticket_count, "errors": len(errors)},
        "errors": [{"message": error} for error in errors],
    }


def _push_payload(
    items: list[PlanItem],
    results: list[tuple[PlanItem, str]],
    ticket_path: Path,
    *,
    write_back: bool,
) -> dict[str, object]:
    result_keys = {item.ticket.path: key for item, key in results}
    local_keys = {
        item.ticket.local_id: key
        for item, key in results
        if item.ticket.local_id
    }
    rendered_items: list[dict[str, object]] = []
    for item in items:
        parent = item.ticket.parent
        rendered_items.append(
            {
                "action": item.action.value,
                "file": _relative_ticket_path(item.ticket.path, ticket_path),
                "local_id": item.ticket.local_id,
                "jira_key": result_keys.get(item.ticket.path, item.ticket.jira_key),
                "project": item.ticket.project,
                "issue_type": item.ticket.issue_type,
                "summary": item.ticket.summary,
                "parent": parent,
                "resolved_parent_key": local_keys.get(parent, item.resolved_parent),
                "changed_fields": item.changed_fields,
                "status": "skipped" if item.action == Action.NOOP else "succeeded",
            }
        )
    return {
        "schema_version": 1,
        "write_back": write_back,
        "summary": _action_summary(items),
        "items": rendered_items,
    }


def _json_error(message: str) -> dict[str, object]:
    return {"schema_version": 1, "error": {"message": message}}


@app.command()
def validate(
    path: Annotated[Path | None, typer.Argument(help="Markdown ticket file or directory")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Emit a machine-readable JSON result")] = False,
) -> None:
    """Validate local Markdown tickets without contacting Jira."""
    _, _, tickets = _load(path)
    errors = validate_ticket_set(tickets)
    if json_output:
        typer.echo(json.dumps(_validation_payload(len(tickets), errors), indent=2, ensure_ascii=False))
        if errors:
            raise typer.Exit(code=1)
        return
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
    json_output: Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON results; requires --yes")] = False,
) -> None:
    """Create/update Jira issues and write created keys back to Markdown."""
    if json_output and not yes:
        typer.echo(json.dumps(_json_error("--json requires --yes"), indent=2))
        raise typer.Exit(code=2)

    settings, ticket_path, tickets = _load(path)
    try:
        with _client(settings) as jira:
            items = build_plan(tickets, jira)
            creates = sum(i.action.value == "CREATE" for i in items)
            updates = sum(i.action.value == "UPDATE" for i in items)
            noops = sum(i.action.value == "NOOP" for i in items)
            if not json_output:
                console.print(
                    f"Plan: [green]{creates} create[/green], "
                    f"[yellow]{updates} update[/yellow], {noops} unchanged"
                )
            if not yes and not typer.confirm("Apply this plan to Jira?"):
                raise typer.Abort()
            results = execute_plan(items, jira, write_back=not no_write_back)
    except (ValueError, JiraError) as exc:
        if json_output:
            typer.echo(json.dumps(_json_error(str(exc)), indent=2, ensure_ascii=False))
        else:
            console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    if json_output:
        typer.echo(
            json.dumps(
                _push_payload(items, results, ticket_path, write_back=not no_write_back),
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    for item, key in results:
        console.print(f"[green]{item.action.value}[/green] {key}  {item.ticket.summary}")
    for item in items:
        if item.action == Action.NOOP:
            console.print(f"[dim]NOOP[/dim] {item.ticket.jira_key}  {item.ticket.summary}")


if __name__ == "__main__":
    app()
