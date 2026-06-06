# Concepts and terminology

A conceptual map of the Research Deep Agent: the channels it speaks over, the
models it runs on, its input/output contract, and the theory behind how it
behaves.

## Channels and interfaces

A *channel* is a way to reach the same agent. They all run the identical
research process and output contract; only the transport differs.

| Channel | Transport | Shape |
| --- | --- | --- |
| CLI | stdin/stdout | one-shot or interactive |
| Control panel | browser → HTTP | natural-language chat UI |
| HTTP API | request/response | `POST /research` → JSON |
| Streaming | SSE (CloudEvents) | `POST /research/stream` → progress + tokens |
| A2UI | SSE (JSON-RPC) | `POST /research/a2ui` → renderable surfaces |
| MCP | Model Context Protocol | `research` / `research_pack` tools |

The agent core is channel-agnostic: a channel is a thin adapter that turns a
question into the agent's input and the agent's output into that channel's
format.

## Models

The *model* is the LLM that drives the orchestrator and sub-agents. It is
vendor-neutral and local-first:

- Resolution order: `RESEARCH_AGENT_MODEL` > a recognised cloud key
  (Anthropic / OpenAI / Google) > `LOCAL_MODEL` > `ollama:tinyllama`.
- With no keys the agent runs fully locally via Ollama; a cloud key switches it
  to a hosted model. Configurable globally, per tenant, or per request.

A model is not the agent. The agent is the orchestration, prompts, tools and
process around whatever model you plug in.

## Inputs and outputs

**Input**: a natural-language question, optionally with a tenant
(`X-Tenant-ID`) and a model override. The agent expects the question to name a
subject and the decision it informs; if it is too vague, the agent stops and
asks rather than guessing.

**Output**: a structured report, always in the same order — Quick answer → Key
findings (each with a source and a confidence tag) → Analysis → Gaps →
Contradictions → Sources → Recommended next step. The Gaps section is mandatory
and never empty. Over the streaming channel the same output arrives as a
sequence of events (accepted → status → token… → completed); over A2UI it
arrives as UI surface messages.

The contract is constant across channels, so a client written for one channel
understands the others.

## Core concepts (the theory)

The agent's behaviour follows a single premise: **the cost of a wrong answer is
higher than the cost of saying "I'm not sure."** Everything below serves it.

- **Triangulation** — an important claim is not treated as solid until two
  independent sources agree. One source is reported as single-source.
- **Evidence categories** — every piece of information is exactly one of: hard
  fact, reported claim, inference, opinion, unverified, or gap. They are never
  blurred.
- **Confidence tags** — HIGH / MEDIUM / LOW / UNVERIFIED on every factual
  claim, so strength is visible, not implied by tone.
- **Source hierarchy** — primary records > expert-reviewed > institutions >
  quality journalism > analyst data > company claims > opinion > unvetted.
- **Honesty over impressiveness** — gaps and contradictions are surfaced, not
  hidden; a missing or compromised data source degrades to a gap, never to a
  confident fabrication.
- **Stop when uncertain** — genuine uncertainty is escalated to the user, not
  papered over.

## Glossary

- **Source pack** — a domain specialist sub-agent (investor, people, market,
  company, technical, sales, general) with its own tool routing order.
- **Critique pack** — the sub-agent that runs the inversion / bias /
  completeness stress-test on a draft before delivery.
- **Tenant** — an isolated caller with its own credentials and model.
- **Tool** — a callable data source (Tavily, Perplexity, Apollo, PitchBook…);
  missing credentials make a tool report a gap, never fabricate.
- **Surface** (A2UI) — a declarative UI description the agent emits for a client
  to render natively.
