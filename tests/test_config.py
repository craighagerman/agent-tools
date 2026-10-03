from agent_tools.jira_sync.config import load_settings


def test_load_settings_reads_jira_credentials_from_dotenv(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text(
        "JIRA_BASE_URL=https://dotenv.example.atlassian.net/\n"
        "JIRA_EMAIL=dotenv@example.com\n"
        "JIRA_API_TOKEN=dotenv-token\n"
        "JIRA_PROJECT=DOT\n",
        encoding="utf-8",
    )
    for name in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_PROJECT"):
        monkeypatch.delenv(name, raising=False)

    settings = load_settings(tmp_path)

    assert settings.base_url == "https://dotenv.example.atlassian.net"
    assert settings.email == "dotenv@example.com"
    assert settings.api_token == "dotenv-token"
    assert settings.project == "DOT"


def test_process_environment_overrides_dotenv(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("JIRA_PROJECT=DOT\n", encoding="utf-8")
    monkeypatch.setenv("JIRA_PROJECT", "PROCESS")

    settings = load_settings(tmp_path)

    assert settings.project == "PROCESS"
