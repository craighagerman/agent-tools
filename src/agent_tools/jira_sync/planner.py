from __future__ import annotations

from .jira import JiraClient
from .models import Action, PlanItem, Ticket


def validate_ticket_set(tickets: list[Ticket]) -> list[str]:
    errors: list[str] = []
    local_ids: dict[str, Ticket] = {}
    for ticket in tickets:
        if not ticket.project:
            errors.append(f"{ticket.path}: no Jira project specified")
        if ticket.local_id:
            if ticket.local_id in local_ids:
                errors.append(f"duplicate local id '{ticket.local_id}': {ticket.path} and {local_ids[ticket.local_id].path}")
            local_ids[ticket.local_id] = ticket

    for ticket in tickets:
        if ticket.parent and not _looks_like_jira_key(ticket.parent) and ticket.parent not in local_ids:
            errors.append(f"{ticket.path}: parent '{ticket.parent}' is neither a Jira key nor a local ticket id")
    return errors


def _looks_like_jira_key(value: str) -> bool:
    head, sep, tail = value.rpartition("-")
    return bool(sep and head and tail.isdigit())


def build_plan(tickets: list[Ticket], jira: JiraClient | None = None) -> list[PlanItem]:
    errors = validate_ticket_set(tickets)
    if errors:
        raise ValueError("\n".join(errors))

    local_ids = {t.local_id: t for t in tickets if t.local_id}
    plan: list[PlanItem] = []
    for ticket in tickets:
        resolved_parent = ticket.parent
        if ticket.parent and not _looks_like_jira_key(ticket.parent):
            parent_ticket = local_ids[ticket.parent]
            resolved_parent = parent_ticket.jira_key

        if ticket.jira_key:
            if jira is None:
                action = Action.UPDATE
                reason = "jira_key present"
            elif jira.issue_exists(ticket.jira_key):
                action = Action.UPDATE
                reason = f"existing issue {ticket.jira_key}"
            else:
                raise ValueError(f"{ticket.path}: jira_key {ticket.jira_key} does not exist")
        else:
            action = Action.CREATE
            reason = "no jira_key"
        plan.append(PlanItem(ticket=ticket, action=action, reason=reason, resolved_parent=resolved_parent))
    return plan
