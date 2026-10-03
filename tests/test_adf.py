from agent_tools.jira_sync.adf import markdown_to_adf


def test_markdown_to_adf_handles_common_blocks():
    adf = markdown_to_adf("## Criteria\n\n- One\n- **Two**\n\n```python\nprint('x')\n```\n")
    assert adf["type"] == "doc"
    assert adf["version"] == 1
    assert adf["content"][0]["type"] == "heading"
    assert any(node["type"] == "bulletList" for node in adf["content"])
    assert any(node["type"] == "codeBlock" for node in adf["content"])
