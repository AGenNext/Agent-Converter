# Research Deep Agent

A [LangChain **deep agent**](https://github.com/langchain-ai/deepagents)
implementation of the **Research Agent build specification (v1.0)**.

It is a universal research agent for a non-technical user who makes business
decisions from its output. Its guiding rule: the cost of a wrong answer is
higher than the cost of saying "I'm not sure." So it triangulates sources,
tags every claim with a confidence level, never hides gaps, and stops to ask
when it is genuinely uncertain.

## Documentation

| Doc | What's in it |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | How the deep agent is structured, with an architectural diagram |
| [docs/usage.md](docs/usage.md) | How-to-use guide: install, configure, run, read the output |
| [docs/configuration.md](docs/configuration.md) | Env vars, model selection, tool keys |
| [docs/design-principles.md](docs/design-principles.md) | The principles behind the build |
| [docs/best-practices.md](docs/best-practices.md) | Using, extending and operating the agent well |
| [docs/extending.md](docs/extending.md) | Wire a premium source, add a pack, add output routing |
| [docs/deployment.md](docs/deployment.md) | Container, Kubernetes, operator, and day-2 ops |
| [docs/ui-mockup.md](docs/ui-mockup.md) | Reference UI ([open the mockup](docs/ui-mockup.html)) |

## Why a deep agent

The deep-agents pattern gives us exactly what the spec asks for:

| Spec concept | Deep-agents mechanism |
| --- | --- |
| The research process (Frame -> Decompose -> ... -> Stress-Test) | Orchestrator `instructions` + the built-in `write_todos` planner |
| Source packs (Section 4), each with its own tool routing | One **sub-agent** per pack, each with a scoped tool allow-list and its own context window |
| Step 8 stress-test (inversion / bias / completeness) | A dedicated `critique` sub-agent |
| Carrying findings between steps without losing detail | The built-in virtual **file system** (`write_file` / `read_file`) used as a scratchpad |
| Verification layer (Perplexity, never sole source) | `perplexity_verify` tool, reached last in every routing order |

## Architecture

```
Orchestrator (research_agent/prompts.py: the "brain", spec 1-3, 5-7)
  |
  |-- write_todos / files (built-in planning + scratchpad)
  |
  +-- task -> sub-agents (research_agent/subagents.py, spec Section 4)
        investor-research   people-research   market-research
        company-research    technical-research sales-research
        general-research    critique
              |
              +-- tools (research_agent/tools.py, spec Section 10)
                    Live:  tavily_search  web_search  web_fetch
                           perplexity_verify  apollo_enrich
                    Stub:  pitchbook_search  factset_query
                           harmonic_lookup  clay_enrich
```

- **`research_agent/prompts.py`** — the orchestrator instructions plus shared
  building blocks (critical-thinking layer, evidence categories, confidence
  tags, source hierarchy, output standards, anti-patterns). A faithful port of
  spec Sections 1, 2, 3, 5, 6, 7.
- **`research_agent/subagents.py`** — one sub-agent per source pack (spec
  Section 4), each with its tool routing order and required output fields.
- **`research_agent/tools.py`** — tool wiring (spec Section 10). Live tools hit
  real APIs; premium sources are honest stubs marked `# TODO(builder)`.
- **`research_agent/agent.py`** — assembles everything via `create_deep_agent`.

## Install

```bash
pip install -r requirements.txt      # or: pip install -e .
cp .env.example .env                 # then fill in the keys you have
```

You need an `ANTHROPIC_API_KEY` (deep agents default to Claude) plus whatever
data tools you want live. Missing keys are fine: that tool reports a gap
instead of fabricating, which is the behaviour the spec mandates.

## Run

```bash
# one-off
python main.py "Research Parkwalk Advisors for Sumandra's GBP 3.2M seed round"

# interactive
python main.py
```

Or from Python:

```python
from research_agent import build_agent

agent = build_agent()
result = agent.invoke(
    {"messages": [{"role": "user", "content": "..."}]}
)
print(result["messages"][-1].content)
```

The agent returns a compiled LangGraph graph, so `.invoke`, `.stream` and
async variants all work, and you can drop it into LangGraph Studio.

## Wiring the premium sources

`pitchbook_search`, `factset_query`, `harmonic_lookup` and `clay_enrich` are
real LangChain tools with the correct signatures, but they return a
"not configured" message until you implement the vendor call. Search for
`# TODO(builder)` in `research_agent/tools.py`, add the API request, and map
the response to a compact JSON summary. On error, return a message (do not
fabricate) so the agent records a gap.

## Tests

```bash
pytest                       # structural checks, offline, no keys
RUN_LIVE_TESTS=1 pytest -s   # the 7 spec test cases, needs keys + manual grading
```

Structural tests assert the agent assembles, every sub-agent has the right
shape and references only real tools, and the orchestrator prompt encodes the
non-negotiable rules. The live cases print output for grading against
`tests/RUBRIC.md` (spec Section 8). Passing threshold: average 4+ across all
criteria, no single score below 3.

## Build phases (spec Section 9)

- **Phase 1 (done here):** brain, investor + people + general packs, output
  standards; Tavily, Apollo, web search/fetch, Perplexity wired live;
  validation scaffold.
- **Phase 2:** market + company packs and the technical / sales packs are
  already defined; wire FactSet, Harmonic, Clay, and add Notion / Google Drive
  output routing.
- **Phase 3:** session memory, a verification pass on the top 3 claims, tool
  parallelism, and the ability to extend a previous output.

## Output destination

The orchestrator asks where to send each result (Notion, Google Drive, chat).
Notion and Google Drive delivery are Phase 2: add them as tools and the
routing instruction is already in the prompt.
