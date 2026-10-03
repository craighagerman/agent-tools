from __future__ import annotations

from typing import Any

from .adf import markdown_to_adf
from .models import Ticket


def fields_for_ticket(ticket: Ticket, parent_key: str | None = None) -> dict[str, Any]:
    """Build the Jira fields managed by jira-sync for a ticket."""
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
    if parent_key:
        fields["parent"] = {"key": parent_key}
    fields.update(ticket.extra_fields)
    return fields


def changed_fields(desired: dict[str, Any], issue: dict[str, Any]) -> list[str]:
    """Return managed field names whose desired and remote values differ."""
    remote = issue.get("fields")
    if not isinstance(remote, dict):
        raise ValueError("Jira issue response does not contain a fields mapping")

    return [
        name
        for name, desired_value in desired.items()
        if not _field_values_equal(name, desired_value, remote.get(name))
    ]


def _field_values_equal(name: str, desired: Any, remote: Any) -> bool:
    if name == "project":
        return _nested_value(desired, "key") == _nested_value(remote, "key")
    if name in {"issuetype", "priority"}:
        return _nested_value(desired, "name") == _nested_value(remote, "name")
    if name == "assignee":
        return _nested_value(desired, "accountId") == _nested_value(remote, "accountId")
    if name == "parent":
        return _nested_value(desired, "key") == _nested_value(remote, "key")
    if name == "labels":
        return sorted(set(desired or [])) == sorted(set(remote or []))
    if name == "description" or (isinstance(desired, dict) and desired.get("type") == "doc"):
        return _normalize_adf(desired) == _normalize_adf(remote)
    return _desired_matches_remote(desired, remote)


def _nested_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return value


def _desired_matches_remote(desired: Any, remote: Any) -> bool:
    if isinstance(desired, dict):
        return isinstance(remote, dict) and all(
            key in remote and _desired_matches_remote(value, remote[key])
            for key, value in desired.items()
        )
    if isinstance(desired, list):
        return (
            isinstance(remote, list)
            and len(desired) == len(remote)
            and all(_desired_matches_remote(left, right) for left, right in zip(desired, remote))
        )
    return desired == remote


def _normalize_adf(value: Any) -> Any:
    if value is None:
        return None

    def clean(item: Any) -> Any:
        if isinstance(item, dict):
            normalized = {
                key: clean(child)
                for key, child in item.items()
                if key != "localId" and child is not None
            }
            return {
                key: child
                for key, child in normalized.items()
                if child not in ({}, [])
            }
        if isinstance(item, list):
            return [clean(child) for child in item]
        return item

    normalized = clean(value)
    if normalized in (
        {},
        {"type": "doc", "version": 1},
        {"type": "doc", "version": 1, "content": [{"type": "paragraph"}]},
    ):
        return None
    return normalized
