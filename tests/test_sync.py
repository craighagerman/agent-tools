from pathlib import Path

from agent_tools.jira_sync.models import Action, CreatedIssue, PlanItem, Ticket
from agent_tools.jira_sync.sync import execute_plan, fields_for


class FakeJira:
    def __init__(self):
        self.created = []
        self.updated = []
        self.next = 100

    def create_issue(self, fields):
        self.created.append(fields)
        self.next += 1
        return CreatedIssue(key=f"ENG-{self.next}")

    def update_issue(self, key, fields):
        self.updated.append((key, fields))


def t(path: Path, summary: str, **kwargs):
    return Ticket(path=path, summary=summary, project="ENG", **kwargs)


def test_execute_orders_parent_before_child(tmp_path):
    parent_path = tmp_path / "parent.md"
    child_path = tmp_path / "child.md"
    parent_path.write_text("---\nid: parent\nproject: ENG\n---\n\n# Parent\n", encoding="utf-8")
    child_path.write_text("---\nid: child\nproject: ENG\nparent: parent\n---\n\n# Child\n", encoding="utf-8")

    parent = t(parent_path, "Parent", local_id="parent")
    child = t(child_path, "Child", local_id="child", parent="parent")
    plan = [
        PlanItem(ticket=child, action=Action.CREATE, reason="new"),
        PlanItem(ticket=parent, action=Action.CREATE, reason="new"),
    ]
    jira = FakeJira()
    results = execute_plan(plan, jira)  # type: ignore[arg-type]
    assert [key for _, key in results] == ["ENG-101", "ENG-102"]
    assert jira.created[1]["parent"] == {"key": "ENG-101"}
    assert "jira_key: ENG-101" in parent_path.read_text()
    assert "jira_key: ENG-102" in child_path.read_text()


def test_fields_include_custom_fields(tmp_path):
    ticket = t(tmp_path / "x.md", "X", extra_fields={"customfield_10042": 5})
    item = PlanItem(ticket=ticket, action=Action.CREATE, reason="new")
    fields = fields_for(item, {})
    assert fields["customfield_10042"] == 5


def test_execute_skips_noop_items(tmp_path):
    ticket = t(tmp_path / "existing.md", "Existing", jira_key="ENG-12")
    item = PlanItem(ticket=ticket, action=Action.NOOP, reason="no managed field changes")
    jira = FakeJira()

    results = execute_plan([item], jira)

    assert results == []
    assert jira.updated == []


def test_execute_sends_only_changed_fields_for_semantic_update(tmp_path):
    ticket = t(tmp_path / "existing.md", "Existing", jira_key="ENG-12", priority="High")
    item = PlanItem(
        ticket=ticket,
        action=Action.UPDATE,
        reason="changed fields: summary",
        changed_fields=["summary"],
    )
    jira = FakeJira()

    execute_plan([item], jira)

    assert jira.updated == [("ENG-12", {"summary": "Existing"})]
