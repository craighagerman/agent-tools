from __future__ import annotations

from markdown_it import MarkdownIt
from markdown_it.token import Token


def _text_node(text: str, marks: list[dict] | None = None) -> dict:
    node: dict = {"type": "text", "text": text}
    if marks:
        node["marks"] = marks
    return node


def _inline_content(token: Token) -> list[dict]:
    children = token.children or []
    content: list[dict] = []
    marks: list[dict] = []
    for child in children:
        if child.type == "text":
            if child.content:
                content.append(_text_node(child.content, marks.copy() or None))
        elif child.type == "code_inline":
            content.append(_text_node(child.content, marks + [{"type": "code"}]))
        elif child.type == "softbreak" or child.type == "hardbreak":
            content.append({"type": "hardBreak"})
        elif child.type == "strong_open":
            marks.append({"type": "strong"})
        elif child.type == "strong_close":
            marks = [m for m in marks if m.get("type") != "strong"]
        elif child.type == "em_open":
            marks.append({"type": "em"})
        elif child.type == "em_close":
            marks = [m for m in marks if m.get("type") != "em"]
        elif child.type == "link_open":
            href = child.attrGet("href")
            marks.append({"type": "link", "attrs": {"href": href}})
        elif child.type == "link_close":
            marks = [m for m in marks if m.get("type") != "link"]
    return content


def markdown_to_adf(markdown: str) -> dict:
    """Convert a practical Markdown subset into Jira Atlassian Document Format."""
    md = MarkdownIt("commonmark")
    tokens = md.parse(markdown)
    root: list[dict] = []
    stack: list[tuple[str, dict, list[dict]]] = []
    current = root
    i = 0

    while i < len(tokens):
        token = tokens[i]
        if token.type in {"paragraph_open", "heading_open"}:
            inline = tokens[i + 1] if i + 1 < len(tokens) and tokens[i + 1].type == "inline" else None
            if token.type == "heading_open":
                level = min(int(token.tag[1:]), 6)
                node = {"type": "heading", "attrs": {"level": level}, "content": _inline_content(inline) if inline else []}
            else:
                node = {"type": "paragraph", "content": _inline_content(inline) if inline else []}
            current.append(node)
            i += 2
            continue

        if token.type in {"fence", "code_block"}:
            attrs = {"language": token.info.strip().split()[0]} if token.info.strip() else None
            node = {"type": "codeBlock", "content": [_text_node(token.content.rstrip("\n"))]}
            if attrs:
                node["attrs"] = attrs
            current.append(node)
        elif token.type == "bullet_list_open":
            node = {"type": "bulletList", "content": []}
            current.append(node)
            stack.append(("list", node, current))
            current = node["content"]
        elif token.type == "ordered_list_open":
            order = token.attrGet("start")
            node = {"type": "orderedList", "attrs": {"order": int(order or 1)}, "content": []}
            current.append(node)
            stack.append(("list", node, current))
            current = node["content"]
        elif token.type == "list_item_open":
            node = {"type": "listItem", "content": []}
            current.append(node)
            stack.append(("item", node, current))
            current = node["content"]
        elif token.type in {"list_item_close", "bullet_list_close", "ordered_list_close"}:
            if stack:
                _, _, previous = stack.pop()
                current = previous
        elif token.type == "blockquote_open":
            node = {"type": "blockquote", "content": []}
            current.append(node)
            stack.append(("blockquote", node, current))
            current = node["content"]
        elif token.type == "blockquote_close":
            if stack:
                _, _, previous = stack.pop()
                current = previous
        elif token.type == "hr":
            current.append({"type": "rule"})
        i += 1

    if not root:
        root = [{"type": "paragraph", "content": []}]
    return {"type": "doc", "version": 1, "content": root}
