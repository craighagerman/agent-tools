from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


ENV_FILE_VARIABLE = "AGENT_TOOLS_ENV_FILE"


def _find_upward(start: Path, filename: str) -> Path | None:
    current = start.expanduser().resolve()
    if current.is_file():
        current = current.parent
    for directory in [current, *current.parents]:
        candidate = directory / filename
        if candidate.is_file():
            return candidate
    return None


def find_environment_file(start: Path | None = None) -> Path | None:
    """Find the highest-precedence dotenv file for an agent-tools command."""
    explicit = os.getenv(ENV_FILE_VARIABLE)
    if explicit:
        explicit_path = Path(explicit).expanduser().resolve()
        if not explicit_path.is_file():
            raise FileNotFoundError(f"{ENV_FILE_VARIABLE} points to a missing file: {explicit_path}")
        return explicit_path

    project_env = _find_upward(start or Path.cwd(), ".env")
    if project_env:
        return project_env

    user_env = Path.home() / ".config" / "agent-tools" / ".env"
    if user_env.is_file():
        return user_env

    return _find_upward(Path(__file__), ".env")


def load_environment(start: Path | None = None) -> Path | None:
    """Load dotenv values without replacing variables already in the process."""
    env_file = find_environment_file(start)
    if env_file and env_file.is_file():
        load_dotenv(dotenv_path=env_file, override=False)
        return env_file
    return None
