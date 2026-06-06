"""Shared helper for reading LangChain message content.

Anthropic (and other providers) may return a message's `content` as a list of
content blocks rather than a plain string, especially during tool use. This
flattens either form to text so callers never silently drop output. Centralised
here so the server, the MCP server and the CLI all behave identically.
"""

from __future__ import annotations


def message_text(content) -> str:
    """Flatten a LangChain message `content` (str or list of blocks) to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return ""
