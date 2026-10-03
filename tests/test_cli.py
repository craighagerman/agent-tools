import json

from typer.testing import CliRunner

from agent_tools.jira_sync.cli import app


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
    }


def test_plan_json_online_reports_verified_updates(tmp_path, monkeypatch):
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

        def issue_exists(self, key):
            return key == "ENG-12"

    monkeypatch.setattr("agent_tools.jira_sync.cli._client", lambda settings: FakeJira())

    result = runner.invoke(app, ["plan", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["mode"] == "online"
    assert payload["summary"] == {"total": 1, "create": 0, "update": 1, "noop": 0}
    assert payload["items"][0]["action"] == "UPDATE"
    assert payload["items"][0]["reason"] == "existing issue ENG-12"
