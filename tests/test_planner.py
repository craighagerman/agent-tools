from pathlib import Path

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
