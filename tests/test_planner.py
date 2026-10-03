from pathlib import Path

import pytest

from agent_tools.jira_sync.issue_fields import fields_for_ticket
from agent_tools.jira_sync.models import Action, Ticket
from agent_tools.jira_sync.planner import build_plan, validate_ticket_set


def ticket(name: str, **kwargs):
    return Ticket(path=Path(name + ".md"), summary=name, project="ENG", **kwargs)


def test_plan_create_and_update_offline():
    plan = build_plan([ticket("new"), ticket("existing", jira_key="ENG-12")])
    assert [p.action for p in plan] == [Action.CREATE, Action.UPDATE]


def test_validation_rejects_unknown_local_parent():
    errors = validate_ticket_set([ticket("child", parent="missing")])
    assert "parent 'missing'" in errors[0]


class FakeJira:
    def __init__(self, issues):
        self.issues = issues

    def get_issue_or_none(self, key, fields=None):
        return self.issues.get(key)


def test_online_plan_detects_semantic_noop():
    existing = ticket(
        "existing",
        jira_key="ENG-12",
        labels=["backend", "agents"],
        priority="High",
        description_markdown="Body",
    )
    remote_fields = fields_for_ticket(existing)
    remote_fields["labels"] = ["agents", "backend"]
    remote_fields["description"]["content"][0]["localId"] = "jira-generated-id"

    plan = build_plan([existing], FakeJira({"ENG-12": {"fields": remote_fields}}))

    assert plan[0].action == Action.NOOP
    assert plan[0].changed_fields == []
    assert plan[0].reason == "no managed field changes"


def test_online_plan_reports_changed_managed_fields():
    existing = ticket(
        "existing",
        jira_key="ENG-12",
        priority="High",
        extra_fields={"customfield_10042": 5},
    )
    remote_fields = fields_for_ticket(existing)
    remote_fields["summary"] = "Old summary"
    remote_fields["priority"] = {"name": "Low"}
    remote_fields["customfield_10042"] = 3

    plan = build_plan([existing], FakeJira({"ENG-12": {"fields": remote_fields}}))

    assert plan[0].action == Action.UPDATE
    assert plan[0].changed_fields == ["summary", "priority", "customfield_10042"]
    assert plan[0].reason == "changed fields: summary, priority, customfield_10042"


def test_online_plan_ignores_unspecified_optional_fields():
    existing = ticket("existing", jira_key="ENG-12")
    remote_fields = fields_for_ticket(existing)
    remote_fields.update(
        {
            "labels": ["managed-in-jira"],
            "priority": {"name": "High"},
            "assignee": {"accountId": "123"},
            "parent": {"key": "ENG-1"},
        }
    )

    plan = build_plan([existing], FakeJira({"ENG-12": {"fields": remote_fields}}))

    assert plan[0].action == Action.NOOP


def test_online_plan_rejects_missing_jira_issue():
    existing = ticket("existing", jira_key="ENG-12")

    with pytest.raises(ValueError, match="jira_key ENG-12 does not exist"):
        build_plan([existing], FakeJira({}))


def test_online_plan_compares_resolved_local_parent_key():
    parent = ticket("parent", local_id="parent", jira_key="ENG-1", issue_type="Epic")
    child = ticket("child", jira_key="ENG-2", parent="parent")
    issues = {
        "ENG-1": {"fields": fields_for_ticket(parent)},
        "ENG-2": {"fields": fields_for_ticket(child, "ENG-1")},
    }

    plan = build_plan([parent, child], FakeJira(issues))

    assert [item.action for item in plan] == [Action.NOOP, Action.NOOP]
    assert plan[1].resolved_parent == "ENG-1"


def test_online_plan_ignores_server_enrichment_of_custom_field_values():
    existing = ticket(
        "existing",
        jira_key="ENG-12",
        extra_fields={"customfield_10042": {"value": "Five"}},
    )
    remote_fields = fields_for_ticket(existing)
    remote_fields["customfield_10042"] = {
        "id": "5",
        "self": "https://example.atlassian.net/rest/api/3/customFieldOption/5",
        "value": "Five",
    }

    plan = build_plan([existing], FakeJira({"ENG-12": {"fields": remote_fields}}))

    assert plan[0].action == Action.NOOP
