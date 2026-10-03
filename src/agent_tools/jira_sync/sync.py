from __future__ import annotations

from typing import Any

from .adf import markdown_to_adf
from .jira import JiraClient
from .markdown import write_jira_key
from .models import Action, PlanItem


def fields_for(item: PlanItem, local_key_map: dict[str, str]) -> dict[str, Any]:
    ticket = item.ticket
    fields: dict[str, Any] = {
        "project": {"key": ticket.project},
        "issuetype": {"name": ticket.issue_type},
        "summary": ticket.summary,
        "description": markdown_to_adf(ticket.description_markdown),
    }
    if ticket.labels:
        fields["labels"] = ticket.labels
    if ticket.priority:
        fields["priority"] = {"name": ticket.priority}
    if ticket.assignee_account_id:
        fields["assignee"] = {"accountId": ticket.assignee_account_id}

    parent = ticket.parent
    if parent:
        parent_key = local_key_map.get(parent, parent)
        fields["parent"] = {"key": parent_key}

    fields.update(ticket.extra_fields)
    return fields


def execute_plan(plan: list[PlanItem], jira: JiraClient, *, write_back: bool = True) -> list[tuple[PlanItem, str]]:
    results: list[tuple[PlanItem, str]] = []
    local_key_map: dict[str, str] = {
        item.ticket.local_id: item.ticket.jira_key
        for item in plan
        if item.ticket.local_id and item.ticket.jira_key
    }

    pending = list(plan)
    while pending:
        progressed = False
        for item in pending[:]:
            parent = item.ticket.parent
            if parent and parent not in local_key_map and not _looks_like_jira_key(parent):
                continue

            fields = fields_for(item, local_key_map)
            if item.action == Action.CREATE:
                created = jira.create_issue(fields)
                key = created.key
                if item.ticket.local_id:
                    local_key_map[item.ticket.local_id] = key
                item.ticket.jira_key = key
                if write_back:
                    write_jira_key(item.ticket.path, key)
                results.append((item, key))
            elif item.action == Action.UPDATE:
                assert item.ticket.jira_key
                jira.update_issue(item.ticket.jira_key, fields)
                results.append((item, item.ticket.jira_key))
            pending.remove(item)
            progressed = True

        if not progressed:
            blocked = ", ".join(str(i.ticket.path) for i in pending)
            raise ValueError(f"Could not resolve parent dependency order for: {blocked}")
    return results


def _looks_like_jira_key(value: str) -> bool:
    head, sep, tail = value.rpartition("-")
    return bool(sep and head and tail.isdigit())
