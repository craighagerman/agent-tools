# Repository Guidelines

## Project Structure & Module Organization

This is a Python 3.11+ package using a `src/` layout. Production code lives in `src/agent_tools/`; the current tool is `src/agent_tools/jira_sync/`, with CLI commands in `cli.py`, Jira transport in `jira.py`, data models in `models.py`, and parsing, planning, and synchronization split into focused modules. Tests live in `tests/`, while reusable Markdown samples belong in `tests/fixtures/`. User-facing documentation is in `README.md` and `Docs/jira-sync.md`.

Keep agent-independent logic in the package rather than in editor- or agent-specific configuration. Add new capabilities as focused subpackages and expose stable command-line entry points through `pyproject.toml`.

## Build, Test, and Development Commands

- `uv sync --extra dev` creates or updates the environment from `uv.lock`, including test dependencies.
- `uv run pytest` runs the complete test suite configured in `pyproject.toml`.
- `uv run pytest tests/test_planner.py -q` runs one test module during iteration.
- `uv run jira-sync --help` verifies the installed CLI entry point.
- `uv run jira-sync validate <path>` validates ticket Markdown without contacting Jira.
- `uv build` produces wheel and source distributions through Hatchling.

An editable pip workflow (`pip install -e '.[dev]'`) is also supported, but keep `uv.lock` current when dependencies change.

## Coding Style & Naming Conventions

Follow standard Python conventions: four-space indentation, `snake_case` for functions and modules, `PascalCase` for classes, and uppercase enum members. Use type annotations and `pathlib.Path`; preserve the existing `from __future__ import annotations` pattern in package modules. Prefer small, deterministic functions and explicit error handling. No formatter or linter is currently configured, so match nearby code and keep imports grouped as standard library, third-party, then local.

## Testing Guidelines

Tests use pytest and `pytest-httpx`. Name files `test_<area>.py` and functions `test_<behavior>()`. Cover both successful behavior and validation/error paths. Use `tmp_path` for filesystem changes, fixtures for representative ticket files, and fake clients for Jira mutations. There is no formal coverage threshold; every behavior change should include a focused regression test.

## Commit & Pull Request Guidelines

The short history uses concise, descriptive commit subjects (for example, `created jira-sync tool for uploading markdown tickets to Jira`). Keep each commit focused and write subjects that state the outcome. Pull requests should explain the motivation, summarize user-visible changes, list tests run, and link relevant issues. Include sample CLI output when command behavior changes. Never commit Jira tokens, `.env` files, or project-specific credentials.
