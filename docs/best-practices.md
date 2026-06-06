# Best practices

How to operate, extend and trust this agent. Split into using it, building on
it, and running it in production.

## Using the agent

- **Name the decision, not just the subject.** "Research Fund X for our GBP
  3.2M seed" gives the agent a fit test to run. "Tell me about Fund X" does
  not.
- **Give your context up front** (sector, stage, geography). It saves a
  clarification round trip and sharpens the fit assessment.
- **Trust the tags, not the tone.** Read confidence tags and the Gaps section
  before acting. HIGH means 2+ independent sources; LOW/UNVERIFIED means
  verify yourself.
- **Expect it to push back.** If your question is vague, the agent asks rather
  than guessing. That is working as designed.
- **Re-run with narrowed scope** when output is broad. "Last 12 months only"
  or "UK only" focuses the search.

## Building on the agent

- **Never let a tool fabricate.** When wiring a premium source, on a missing
  key or an error return a short message (the existing stubs show the
  pattern). Do not return invented data, and do not raise — let the agent
  record a gap and move on.
- **Keep tool docstrings sharp.** The model routes on them. Say what the tool
  is for and when to reach for it, matching the pack's routing order.
- **Put rules in `prompts.py`, not in a single pack.** Anything that should
  apply everywhere (a new anti-pattern, a tagging rule) goes in the shared
  blocks so every sub-agent inherits it.
- **Scope each pack's tools deliberately.** Give a pack only the tools its
  routing order names. Over-wide tool access makes the model pick the wrong
  tool.
- **Add a pack as a sub-agent, not as orchestrator bloat.** Follow the
  existing `SubAgent` dicts: name, description (this is the routing signal),
  `system_prompt` with the tool order and required output, scoped `tools`.
  See [extending](extending.md).
- **Run the structural tests after any change** (`pytest -q`). They catch
  broken tool references, missing packs, and prompts that lost a core rule.

## Choosing and configuring the model

- **Default is `anthropic:claude-sonnet-4-5`.** Override with the
  `RESEARCH_AGENT_MODEL` env var or by passing `model=` to `build_agent()`.
- **Use a strong model for the orchestrator.** It plans, synthesises and runs
  the stress-test. A weaker model here shows up as shallow synthesis and
  missed contradictions.
- **You can give a pack its own model.** A `SubAgent` may set `"model":
  "provider:name"` to override per pack (for example a cheaper model for
  simple enrichment).

## Cost and latency

- **Sub-agents fan out.** A full investor dig can make many tool calls. Start
  with the cheapest useful tool set (model + Tavily) and add premium sources
  as needed.
- **The filesystem scratchpad keeps context small.** Sub-agents write detail
  to `findings_*.md` and return short summaries, so the orchestrator's context
  stays lean. Preserve this pattern when adding packs.
- **`perplexity_verify` runs last, on key claims only.** It is a cross-check,
  not a primary search. Do not move it earlier in a routing order.

## Trust and safety

- **Validate before relying on it.** Run `RUN_LIVE_TESTS=1 pytest -s` and
  grade against `tests/RUBRIC.md`. Bar: average 4+, no single score below 3.
- **Treat tool output as untrusted.** Web and enrichment results can be wrong
  or adversarial. The triangulation and source-tier rules exist for this;
  don't bypass them.
- **Keep secrets in `.env`.** It is gitignored. Never hardcode keys in
  `tools.py` or commit a real `.env`.
- **Financial, legal and tax answers are general.** The general pack already
  states the user should verify with a qualified professional. Keep that.

## Output handling

- **Confirm the destination once per session.** The agent asks where to send
  output; if the user stated a preference earlier, follow it without
  re-asking.
- **Archive findings files if they matter.** `findings_*.md` live in agent
  state for the run. Persist them (or wire Notion / Google Drive output) if
  you need a durable record.
