from pathlib import Path

from agent_tools.jira_sync.markdown import discover_tickets, parse_ticket, write_jira_key


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_ticket_uses_h1_as_summary():
    ticket = parse_ticket(FIXTURES / "child.md")
    assert ticket.summary == "Add tracing"
    assert ticket.local_id == "tracing-story"
    assert ticket.parent == "platform-epic"
    assert "Acceptance Criteria" in ticket.description_markdown
    assert "# Add tracing" not in ticket.description_markdown


def test_discover_tickets():
    tickets = discover_tickets(FIXTURES)
    assert [t.path.name for t in tickets] == ["child.md", "parent.md"]


def test_write_jira_key(tmp_path):
    path = tmp_path / "ticket.md"
    path.write_text("---\nid: demo\n---\n\n# Demo\n\nBody\n", encoding="utf-8")
    write_jira_key(path, "ENG-42")
    ticket = parse_ticket(path)
    assert ticket.jira_key == "ENG-42"
    assert ticket.summary == "Demo"
