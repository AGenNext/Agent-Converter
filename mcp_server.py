"""MCP server interface for the Research deep agent.

Exposes the agent over the Model Context Protocol so other agents, IDEs, and
MCP-capable clients can call it as a tool. Built on the MCP Python SDK's
FastMCP.

Run over stdio (the usual transport for local MCP clients):
    python mcp_server.py

Or over HTTP for remote clients:
    MCP_TRANSPORT=streamable-http python mcp_server.py

Register with an MCP client (stdio example):
    {
      "mcpServers": {
        "research-agent": { "command": "python", "args": ["mcp_server.py"] }
      }
    }

Tools exposed:
    research(question)        run the full research process, return the report
    research_pack(question, pack)
                              run research, hinting which source pack to use
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from research_agent import build_agent
from research_agent.content import message_text

mcp = FastMCP("research-agent")

# Build the agent once and reuse it across tool calls.
_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


def _run(question: str) -> str:
    result = _get_agent().invoke(
        {"messages": [{"role": "user", "content": question}]}
    )
    return message_text(result["messages"][-1].content)


@mcp.tool()
def research(question: str) -> str:
    """Research a question and return an honest, well-sourced, confidence-tagged
    report (Quick answer, Key findings, Analysis, Gaps, Contradictions, Sources,
    Next step). The agent will note if the question is too vague to answer."""
    return _run(question)


@mcp.tool()
def research_pack(question: str, pack: str) -> str:
    """Research a question, hinting which source pack to use. `pack` is one of:
    investor, people, market, company, technical, sales, general. Useful when
    you already know the domain and want to steer routing."""
    hint = (
        f"(Use the {pack} research pack for this.)\n\n{question}"
        if pack
        else question
    )
    return _run(hint)


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
