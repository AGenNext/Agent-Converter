# Extending the agent

Three common extensions: wiring a premium data source, adding a new source
pack, and adding an output destination. Each follows an existing pattern.

## Wire a premium data source

The stubs (`pitchbook_search`, `factset_query`, `harmonic_lookup`,
`clay_enrich`) are real tools that return "not configured" until you implement
the vendor call. Find the integration point by searching `# TODO(builder)` in
`research_agent/tools.py`.

```python
@tool
def pitchbook_search(query: str, entity_type: str = "any") -> str:
    """..."""
    key = os.environ.get("PITCHBOOK_API_KEY")
    if not key:
        return _missing("PITCHBOOK_API_KEY", "PitchBook")
    try:
        resp = requests.get(
            "https://api.pitchbook.com/...",
            headers={"Authorization": f"Bearer {key}"},
            params={"q": query, "type": entity_type},
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except Exception as exc:
        return f"[pitchbook_search failed] {exc}"   # gap, never fabricate
    # Map to a compact JSON summary the model can read.
    return json.dumps(_summarise(resp.json()), indent=2, default=str)
```

Rules: on a missing key or an error, return a message (do not raise, do not
invent data). Keep the return value compact JSON or plain text. Do not change
the function signature, so the packs that already reference it keep working.

## Add a new source pack

A pack is a `SubAgent` dict in `research_agent/subagents.py`.

1. Write the pack prompt: its tool routing order and the required output
   fields, ending with the shared `_STANDARDS` block.
2. Define the dict and scope its `tools` to the tools its routing order names.

```python
from research_agent.tools import tavily_search, web_search, web_fetch, perplexity_verify

LEGAL_RESEARCH = {
    "name": "legal-research",
    "description": (
        "Research statutes, regulations, case law and compliance questions. "
        "Use for any legal or regulatory question. Always note jurisdiction."
    ),
    "system_prompt": f\"\"\"
You are the Legal and Regulatory Research specialist.

TOOL ROUTING ORDER:
1. web_search - official government / regulator sources, established law firms.
2. web_fetch - read the statute, ruling or guidance found.
3. tavily_search - context and commentary.
4. perplexity_verify - cross-check. Never the sole source.

ALWAYS note the jurisdiction. Prefer primary records over news. State that
this is general information, not legal advice.

{{_STANDARDS}}
\"\"\".strip(),
    "tools": [web_search, web_fetch, tavily_search, perplexity_verify],
}
```

3. Add it to `ALL_SUBAGENTS`.
4. Add a routing line for it in the orchestrator's delegation list in
   `research_agent/prompts.py` so the orchestrator knows when to pick it.
5. Run `pytest -q` — the structural tests confirm the pack is registered and
   references only real tools.

The `description` is the routing signal the orchestrator reads, so make it
specific and action-oriented.

## Add an output destination (Notion, Google Drive)

The orchestrator already asks where to send results. To make a destination
real, add it as a tool and register it.

```python
@tool
def save_to_notion(title: str, markdown: str) -> str:
    """Save a finished research output to Notion. Returns the page URL."""
    # call the Notion API; return the URL or an error message
    ...
```

Add it to `ALL_TOOLS` in `tools.py`, and add a line to the orchestrator's
output-destination instruction telling it the tool exists. Keep delivery tools
separate from research tools so packs do not accidentally call them mid-search.

## Change a global rule

Edit the relevant block in `research_agent/prompts.py` (for example
`ANTI_PATTERNS` or `CONFIDENCE_TAGS`). Because both the orchestrator and every
sub-agent import these blocks, the change propagates everywhere. Re-run
`pytest -q`; `test_orchestrator_encodes_core_rules` guards the must-have rules.
