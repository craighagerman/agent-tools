from __future__ import annotations

import os
from pathlib import Path
from typing import Any
import tomllib

from pydantic import BaseModel


class JiraSettings(BaseModel):
    base_url: str | None = None
    email: str | None = None
    api_token: str | None = None
    project: str | None = None
    ticket_directory: str = "tickets"

    @property
    def has_credentials(self) -> bool:
        return bool(self.base_url and self.email and self.api_token)


def _find_project_config(start: Path) -> Path | None:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for directory in [current, *current.parents]:
        candidate = directory / ".ai-tools.toml"
        if candidate.exists():
            return candidate
    return None


def load_settings(start: Path | None = None) -> JiraSettings:
    start = start or Path.cwd()
    values: dict[str, Any] = {}
    config_path = _find_project_config(start)
    if config_path:
        with config_path.open("rb") as handle:
            raw = tomllib.load(handle)
        values.update(raw.get("jira", {}))

    env_map = {
        "base_url": "JIRA_BASE_URL",
        "email": "JIRA_EMAIL",
        "api_token": "JIRA_API_TOKEN",
        "project": "JIRA_PROJECT",
    }
    for key, env_name in env_map.items():
        if os.getenv(env_name):
            values[key] = os.environ[env_name]

    if values.get("base_url"):
        values["base_url"] = str(values["base_url"]).rstrip("/")
    return JiraSettings(**values)
