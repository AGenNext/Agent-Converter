# How to use

A practical guide to running the Research deep agent and getting good output.

## 1. Install

```bash
git clone <repo-url>
cd Agent-Converter
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # or: pip install -e .
```

Requires Python 3.10+.

## 2. Configure keys

```bash
cp .env.example .env
```

Fill in `.env`. The only hard requirement is a model key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Then add whatever data tools you have. Each one is optional; a missing key
makes that tool report a gap instead of fabricating (see
[best practices](best-practices.md)).

```
TAVILY_API_KEY=...        # web research (recommended first)
PERPLEXITY_API_KEY=...     # verification layer
APOLLO_API_KEY=...         # people enrichment
```

See [configuration](configuration.md) for the full list and model overrides.

## 3. Run

One-off question:

```bash
python main.py "Research Parkwalk Advisors for Sumandra's GBP 3.2M seed round"
```

Interactive session:

```bash
python main.py
> What is the global market size for digital twins in aerospace?
> exit
```

From Python:

```python
from research_agent import build_agent

agent = build_agent()
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Profile Anthropic as a company"}]}
)
print(result["messages"][-1].content)
```

`build_agent()` returns a compiled LangGraph graph, so `.invoke`, `.stream`,
and the async variants all work, and you can load it in LangGraph Studio.

## 4. Write good prompts

The agent is built to refuse vague questions and ask for clarification, which
costs you a round trip. You get faster, better answers by including:

- **The subject**, named precisely. "Parkwalk Advisors", not "that deep tech
  fund".
- **The decision** it informs. "...for our GBP 3.2M seed round" tells the
  investor pack what fit to assess.
- **Your context**. Sector, stage, geography, what you already know.
- **Scope**. "Last 12 months only" or "UK market only" narrows the search.

Compare:

> Bad: "Tell me about Parkwalk."
>
> Good: "Research Parkwalk Advisors as a potential lead for Sumandra's GBP
> 3.2M seed round. We are a UK aerospace deep-tech company. I want to know if
> they fit on stage, cheque size, sector and geography, and any red flags."

## 5. Read the output

Every answer follows the same structure:

| Section | What it gives you |
| --- | --- |
| Quick answer | The direct conclusion in 2-4 sentences |
| Key findings | The facts, each with a source and a confidence tag |
| Analysis | What it means for your decision (interpretation, labelled) |
| Gaps and unknowns | What could not be confirmed (never empty) |
| Contradictions | Where credible sources disagree |
| Sources | Each tagged with a credibility tier |
| Recommended next step | One or two concrete actions |

Read the **confidence tags** and the **gaps** section first. A HIGH tag means
2+ independent sources agree; LOW or UNVERIFIED means treat it with care.

## 6. Send the output somewhere

At the end of a task the agent asks where to send the result (Notion, Google
Drive, chat). Notion and Google Drive delivery are Phase 2: wire them as tools
and the routing prompt is already in place. Until then, copy from chat.

## 7. Validate it before you trust it

Run the spec's test cases against your own keys and grade the output:

```bash
RUN_LIVE_TESTS=1 pytest -s tests/test_validation.py
```

Score each case against [`tests/RUBRIC.md`](../tests/RUBRIC.md). Passing bar:
average 4+ across all criteria, no single score below 3.
