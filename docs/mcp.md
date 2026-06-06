# MCP interface

The agent is exposed over the [Model Context Protocol](https://modelcontextprotocol.io)
so other agents, IDEs, and MCP-capable clients can call it as a tool. See
`mcp_server.py` (built on the MCP Python SDK's FastMCP).

## Tools

| Tool | Arguments | Returns |
| --- | --- | --- |
| `research` | `question: str` | The full research report (markdown) |
| `research_pack` | `question: str`, `pack: str` | Report, hinting which pack to use |

`pack` is one of: `investor`, `people`, `market`, `company`, `technical`,
`sales`, `general`.

## Run it

Over stdio (the usual transport for local clients):

```bash
python mcp_server.py
```

Over HTTP for remote clients:

```bash
MCP_TRANSPORT=streamable-http python mcp_server.py
```

The agent needs its usual environment (`ANTHROPIC_API_KEY`, plus any data tool
keys). Load them before launching.

## Register with a client

Stdio example (Claude Desktop, Cursor, etc.):

```json
{
  "mcpServers": {
    "research-agent": {
      "command": "python",
      "args": ["mcp_server.py"],
      "env": { "ANTHROPIC_API_KEY": "sk-ant-...", "TAVILY_API_KEY": "..." }
    }
  }
}
```

Then call the `research` tool with a natural-language question. Missing data
keys degrade to gaps, never to fabrication, exactly as in the other interfaces.
