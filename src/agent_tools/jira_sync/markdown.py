from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import Ticket


FRONT_MATTER_DELIMITER = "---"


def split_front_matter(text: str) -> tuple[dict[str, Any], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONT_MATTER_DELIMITER:
        return {}, text.strip()

    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == FRONT_MATTER_DELIMITER)
    except StopIteration as exc:
        raise ValueError("YAML front matter starts with '---' but has no closing '---'") from exc

    metadata = yaml.safe_load("\n".join(lines[1:end])) or {}
    if not isinstance(metadata, dict):
        raise ValueError("YAML front matter must be a mapping")
    body = "\n".join(lines[end + 1 :]).strip()
    return metadata, body


def _first_h1(body: str) -> tuple[str | None, str]:
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            remaining = lines[:i] + lines[i + 1 :]
            return title, "\n".join(remaining).strip()
    return None, body


def parse_ticket(path: Path, default_project: str | None = None) -> Ticket:
    text = path.read_text(encoding="utf-8")
    meta, body = split_front_matter(text)
    h1, body_without_h1 = _first_h1(body)

    summary = meta.get("summary") or meta.get("title") or h1
    if not summary:
        raise ValueError("Ticket needs either front-matter 'summary'/'title' or a '# Heading'")

    known = {
        "id", "local_id", "jira_key", "project", "type", "issue_type", "summary", "title",
        "labels", "priority", "parent", "assignee_account_id", "fields",
    }
    extra_fields = dict(meta.get("fields") or {})
    for key, value in meta.items():
        if key not in known:
            extra_fields[key] = value

    return Ticket(
        path=path,
        local_id=meta.get("id") or meta.get("local_id"),
        jira_key=meta.get("jira_key"),
        project=meta.get("project") or default_project,
        issue_type=meta.get("type") or meta.get("issue_type") or "Task",
        summary=summary,
        description_markdown=body_without_h1 if h1 and not (meta.get("summary") or meta.get("title")) else body,
        labels=meta.get("labels") or [],
        priority=meta.get("priority"),
        parent=meta.get("parent"),
        assignee_account_id=meta.get("assignee_account_id"),
        extra_fields=extra_fields,
    )


def discover_tickets(path: Path, default_project: str | None = None) -> list[Ticket]:
    if path.is_file():
        paths = [path]
    elif path.is_dir():
        paths = sorted(p for p in path.rglob("*.md") if p.is_file())
    else:
        raise FileNotFoundError(path)
    return [parse_ticket(p, default_project=default_project) for p in paths]


def write_jira_key(path: Path, jira_key: str) -> None:
    text = path.read_text(encoding="utf-8")
    meta, body = split_front_matter(text)
    meta["jira_key"] = jira_key
    dumped = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).rstrip()
    rendered = f"---\n{dumped}\n---\n\n{body.rstrip()}\n"
    path.write_text(rendered, encoding="utf-8")
