import os

import pytest

from agent_tools.environment import find_environment_file, load_environment


def test_load_environment_finds_dotenv_above_start_path(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("AGENT_TOOLS_TEST_VALUE=from-dotenv\n", encoding="utf-8")
    nested = tmp_path / "tickets" / "nested"
    nested.mkdir(parents=True)
    monkeypatch.delenv("AGENT_TOOLS_TEST_VALUE", raising=False)

    loaded = load_environment(nested)

    assert loaded == env_file
    assert os.environ.get("AGENT_TOOLS_TEST_VALUE") == "from-dotenv"


def test_process_environment_takes_precedence(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("AGENT_TOOLS_TEST_VALUE=from-dotenv\n", encoding="utf-8")
    monkeypatch.setenv("AGENT_TOOLS_TEST_VALUE", "from-process")

    load_environment(tmp_path)

    assert os.environ.get("AGENT_TOOLS_TEST_VALUE") == "from-process"


def test_explicit_environment_file_takes_precedence(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    (project / ".env").write_text("SOURCE=project\n", encoding="utf-8")
    explicit = tmp_path / "shared.env"
    explicit.write_text("SOURCE=explicit\n", encoding="utf-8")
    monkeypatch.setenv("AGENT_TOOLS_ENV_FILE", str(explicit))

    assert find_environment_file(project) == explicit


def test_missing_explicit_environment_file_is_an_error(tmp_path, monkeypatch):
    missing = tmp_path / "missing.env"
    monkeypatch.setenv("AGENT_TOOLS_ENV_FILE", str(missing))

    with pytest.raises(FileNotFoundError, match="AGENT_TOOLS_ENV_FILE points to a missing file"):
        load_environment(tmp_path)
