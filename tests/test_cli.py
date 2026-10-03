import json

from typer.testing import CliRunner

from agent_tools.jira_sync.cli import app
from agent_tools.jira_sync.models import CreatedIssue


runner = CliRunner()


def write_ticket(path, front_matter: str, title: str) -> None:
    path.write_text(f"---\n{front_matter}\n---\n\n# {title}\n", encoding="utf-8")


def test_plan_json_offline_emits_structured_plan(tmp_path):
    write_ticket(
        tmp_path / "epic.md",
        "id: platform\nproject: ENG\ntype: Epic\npriority: High",
        "Platform",
    )
    write_ticket(
        tmp_path / "story.md",
        "id: tracing\nproject: ENG\ntype: Story\nparent: platform\nlabels: [agents]",
        "Add tracing",
    )
    write_ticket(
        tmp_path / "update.md",
        "jira_key: ENG-12\nproject: ENG\ntype: Task",
        "Update docs",
    )

    result = runner.invoke(app, ["plan", str(tmp_path), "--offline", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == 1
    assert payload["mode"] == "offline"
    assert payload["summary"] == {"total": 3, "create": 2, "update": 1, "noop": 0}
    assert [item["file"] for item in payload["items"]] == ["epic.md", "story.md", "update.md"]
    assert payload["items"][1] == {
        "action": "CREATE",
        "file": "story.md",
        "local_id": "tracing",
        "jira_key": None,
        "project": "ENG",
        "issue_type": "Story",
        "summary": "Add tracing",
        "parent": "platform",
        "resolved_parent_key": None,
        "priority": None,
        "labels": ["agents"],
        "reason": "no jira_key",
        "changed_fields": [],
    }


def test_plan_json_online_reports_verified_updates(tmp_path, monkeypatch):
    write_ticket(
        tmp_path / "existing.md",
        "jira_key: ENG-12\nproject: ENG\ntype: Task",
        "Existing ticket",
    )

    class FakeJira:
        def __init__(self):
            self.updated = []

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def get_issue_or_none(self, key, fields=None):
            return {
                "key": key,
                "fields": {
                    "project": {"key": "ENG"},
                    "issuetype": {"name": "Task"},
                    "summary": "Old summary",
                    "description": None,
                },
            }

    monkeypatch.setattr("agent_tools.jira_sync.cli._client", lambda settings: FakeJira())

    result = runner.invoke(app, ["plan", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["mode"] == "online"
    assert payload["summary"] == {"total": 1, "create": 0, "update": 1, "noop": 0}
    assert payload["items"][0]["action"] == "UPDATE"
    assert payload["items"][0]["reason"] == "changed fields: summary"
    assert payload["items"][0]["changed_fields"] == ["summary"]


def test_plan_json_online_reports_noop(tmp_path, monkeypatch):
    write_ticket(
        tmp_path / "existing.md",
        "jira_key: ENG-12\nproject: ENG\ntype: Task",
        "Existing ticket",
    )

    class FakeJira:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def get_issue_or_none(self, key, fields=None):
            return {
                "key": key,
                "fields": {
                    "project": {"key": "ENG"},
                    "issuetype": {"name": "Task"},
                    "summary": "Existing ticket",
                    "description": None,
                },
            }

    monkeypatch.setattr("agent_tools.jira_sync.cli._client", lambda settings: FakeJira())

    result = runner.invoke(app, ["plan", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["summary"] == {"total": 1, "create": 0, "update": 0, "noop": 1}
    assert payload["items"][0]["action"] == "NOOP"
    assert payload["items"][0]["changed_fields"] == []


def test_validate_json_reports_success(tmp_path):
    write_ticket(tmp_path / "ticket.md", "id: ticket\nproject: ENG", "Ticket")

    result = runner.invoke(app, ["validate", str(tmp_path), "--json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "schema_version": 1,
        "valid": True,
        "summary": {"tickets": 1, "errors": 0},
        "errors": [],
    }


def test_validate_json_reports_errors_with_nonzero_exit(tmp_path):
    write_ticket(
        tmp_path / "ticket.md",
        "id: ticket\nproject: ENG\nparent: missing",
        "Ticket",
    )

    result = runner.invoke(app, ["validate", str(tmp_path), "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["valid"] is False
    assert payload["summary"] == {"tickets": 1, "errors": 1}
    assert "parent 'missing'" in payload["errors"][0]["message"]


def test_push_json_requires_yes(tmp_path):
    write_ticket(tmp_path / "ticket.md", "id: ticket\nproject: ENG", "Ticket")

    result = runner.invoke(app, ["push", str(tmp_path), "--json"])

    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["message"] == "--json requires --yes"


def test_push_json_reports_created_and_updated_issues(tmp_path, monkeypatch):
    write_ticket(
        tmp_path / "create.md",
        "id: new-ticket\nproject: ENG\ntype: Task",
        "New ticket",
    )
    write_ticket(
        tmp_path / "update.md",
        "jira_key: ENG-12\nproject: ENG\ntype: Task",
        "Existing ticket",
    )

    class FakeJira:
        def __init__(self):
            self.updated = []

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def get_issue_or_none(self, key, fields=None):
            return {
                "key": key,
                "fields": {
                    "project": {"key": "ENG"},
                    "issuetype": {"name": "Task"},
                    "summary": "Old summary",
                    "description": None,
                },
            }

        def create_issue(self, fields):
            return CreatedIssue(key="ENG-101")

        def update_issue(self, key, fields):
            self.updated.append((key, fields))

    jira = FakeJira()
    monkeypatch.setattr("agent_tools.jira_sync.cli._client", lambda settings: jira)

    result = runner.invoke(
        app,
        ["push", str(tmp_path), "--json", "--yes", "--no-write-back"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["write_back"] is False
    assert payload["summary"] == {"total": 2, "create": 1, "update": 1, "noop": 0}
    assert [(item["action"], item["jira_key"]) for item in payload["items"]] == [
        ("CREATE", "ENG-101"),
        ("UPDATE", "ENG-12"),
    ]
    assert all(item["status"] == "succeeded" for item in payload["items"])
    assert jira.updated == [("ENG-12", {"summary": "Existing ticket"})]


def test_push_json_reports_noop_as_skipped(tmp_path, monkeypatch):
    write_ticket(
        tmp_path / "existing.md",
        "jira_key: ENG-12\nproject: ENG\ntype: Task",
        "Existing ticket",
    )

    class FakeJira:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def get_issue_or_none(self, key, fields=None):
            return {
                "key": key,
                "fields": {
                    "project": {"key": "ENG"},
                    "issuetype": {"name": "Task"},
                    "summary": "Existing ticket",
                    "description": None,
                },
            }

        def update_issue(self, key, fields):
            raise AssertionError("NOOP issue must not be updated")

    monkeypatch.setattr("agent_tools.jira_sync.cli._client", lambda settings: FakeJira())

    result = runner.invoke(app, ["push", str(tmp_path), "--json", "--yes"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["summary"] == {"total": 1, "create": 0, "update": 0, "noop": 1}
    assert payload["items"][0]["status"] == "skipped"
