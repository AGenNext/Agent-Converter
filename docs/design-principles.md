# Design principles

The principles behind how this agent is built. They come straight from the
spec's core stance: **the cost of a wrong answer is higher than the cost of
saying "I'm not sure."** Everything below serves that.

## 1. Honesty over impressiveness

The agent's job is to give the full, honest picture, not the most
confident-sounding answer. Concretely:

- Every factual claim carries a confidence tag (HIGH / MEDIUM / LOW /
  UNVERIFIED).
- The Gaps section is mandatory and never empty.
- Contradictions are surfaced with both sides, never silently resolved.

If output ever reads like marketing copy, that is a bug.

## 2. Never fabricate, ever

This is the hardest rule and it shapes the code, not just the prompt. When a
data tool has no API key or returns nothing, it returns a clear
"not configured" / "no match" message rather than guessing. The agent records
that as a gap. A missing integration degrades the answer's completeness; it
never degrades its truthfulness.

## 3. Triangulate before asserting

An important claim is not "solid" until it appears in 2+ independent sources.
One source is reported as single-source. A news article quoting a press
release counts as one source, not two. This is why every pack's tool routing
ends with `perplexity_verify` as a cross-check, never as the only source.

## 4. Stop when genuinely uncertain

When the agent cannot answer a sub-question, or sources conflict and cannot be
reconciled, it stops and asks the user rather than papering over the gap with
a best guess. Asking a clarifying question is cheaper than a confident wrong
answer.

## 5. Decompose, then go wide before deep

Every task is broken into 3-7 answerable sub-questions before any tool runs.
For each, the agent searches across multiple sources (breadth) before drilling
into any one (depth). This prevents the classic failure of one broad search
that "looks done" but misses contradicting evidence.

## 6. Separate fact from interpretation

The output keeps hard facts, reported claims, inferences and opinions in
distinct buckets, and the structure enforces it: findings are facts with
sources; the Analysis section is explicitly labelled interpretation. A reader
should never have to guess which is which.

## 7. Specialisation through sub-agents

Each research domain has a different source hierarchy and tool order, so each
is its own sub-agent with a scoped tool allow-list and a fresh context window.
The orchestrator stays a thin planner-synthesiser. This keeps prompts focused,
stops the model reaching for the wrong tool, and lets deep digs run without
crowding each other's context.

## 8. Rules defined once, applied everywhere

The critical-thinking layer, evidence categories, confidence tags, source
hierarchy and anti-patterns live in one place (`prompts.py`) and are injected
into both the orchestrator and every sub-agent. A sub-agent running in
isolation still carries the full standard, and there is a single source of
truth to edit.

## 9. Built for verification

The agent ships with the spec's 7 validation cases and a scoring rubric. The
design assumes you will test it against known answers and grade it before
trusting it with real decisions. Honesty you cannot measure is just a claim.

## 10. Graceful degradation

The whole system runs on whatever subset of tools you have wired. No PitchBook
key? The investor pack leans on Tavily and web search and flags the structured
data as a gap. The agent is useful on day one with just a model key and
Tavily, and gets sharper as you connect more sources.
