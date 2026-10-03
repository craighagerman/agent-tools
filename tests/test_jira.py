from agent_tools.jira_sync.jira import JiraClient


def test_get_issue_or_none_returns_issue(httpx_mock):
    httpx_mock.add_response(
        url="https://example.atlassian.net/rest/api/3/issue/ENG-12",
        json={"key": "ENG-12", "fields": {"summary": "Example"}},
    )

    with JiraClient("https://example.atlassian.net", "user@example.com", "token") as jira:
        issue = jira.get_issue_or_none("ENG-12")

    assert issue == {"key": "ENG-12", "fields": {"summary": "Example"}}


def test_get_issue_or_none_returns_none_for_404(httpx_mock):
    httpx_mock.add_response(
        url="https://example.atlassian.net/rest/api/3/issue/ENG-404",
        status_code=404,
    )

    with JiraClient("https://example.atlassian.net", "user@example.com", "token") as jira:
        issue = jira.get_issue_or_none("ENG-404")

    assert issue is None


def test_get_issue_or_none_requests_selected_fields(httpx_mock):
    httpx_mock.add_response(
        url=(
            "https://example.atlassian.net/rest/api/3/issue/ENG-12"
            "?fields=summary%2Ccustomfield_10042"
        ),
        json={"key": "ENG-12", "fields": {"summary": "Example", "customfield_10042": 5}},
    )

    with JiraClient("https://example.atlassian.net", "user@example.com", "token") as jira:
        issue = jira.get_issue_or_none("ENG-12", fields=["summary", "customfield_10042"])

    assert issue is not None
    assert issue["fields"]["customfield_10042"] == 5
