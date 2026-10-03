from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class Action(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    NOOP = "NOOP"


class Ticket(BaseModel):
    path: Path
    local_id: str | None = None
    jira_key: str | None = None
    project: str | None = None
    issue_type: str = "Task"
    summary: str
    description_markdown: str = ""
    labels: list[str] = Field(default_factory=list)
    priority: str | None = None
    parent: str | None = None
    assignee_account_id: str | None = None
    extra_fields: dict[str, object] = Field(default_factory=dict)

    @field_validator("summary")
    @classmethod
    def summary_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("summary must not be blank")
        return value.strip()

    @field_validator("labels", mode="before")
    @classmethod
    def normalize_labels(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return list(value)  # type: ignore[arg-type]


class PlanItem(BaseModel):
    ticket: Ticket
    action: Action
    reason: str
    resolved_parent: str | None = None
    changed_fields: list[str] = Field(default_factory=list)


class CreatedIssue(BaseModel):
    key: str
    id: str | None = None
    self_url: str | None = Field(default=None, alias="self")

    model_config = {"populate_by_name": True}
