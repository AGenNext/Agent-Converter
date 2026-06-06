# UI mockup

The agent ships as a CLI and a Python library, but it is designed to sit behind
a chat UI. This is a reference mockup of what that interface looks like, so the
output structure and the agent's guarantees are visible to a non-technical
user.

Open [`ui-mockup.html`](ui-mockup.html) in a browser to see it rendered. It is
a single self-contained file (no build, no dependencies).

## What the mockup shows

A three-region layout built around the spec's output standards:

**Left — source packs and history.** The user (or the orchestrator's router)
selects the active pack: Investor, People, Market, Company, Technical, Sales,
General. Recent research sessions sit below for quick return.

**Top — run context.** The model in use and the live tools for this run, so
the user can see what the answer is grounded in.

**Centre — the conversation.** The user's question, then the agent's response
rendered as the mandated structure, in order:

| Region | Maps to spec output section |
| --- | --- |
| Plan strip (todos) | The decomposition / `write_todos` step |
| Quick answer | A. Quick answer |
| Key findings, each with a confidence chip | B. Key findings + 5.2 tags |
| Analysis | C. Analysis |
| Gaps and unknowns (amber panel) | D. Gaps (mandatory, never empty) |
| Contradictions (blue panel) | E. Contradictions |
| Sources, each with a tier badge | F. Sources + Section 6 hierarchy |
| Recommended next step (numbered) | G. Recommended next step |

**Bottom — composer and destination.** The input box plus the "send result
to" choice (Chat / Notion / Google Drive), matching the spec's output-routing
step.

## Design choices that carry the spec's intent

- **Confidence is colour, not just text.** HIGH is green, MEDIUM amber, LOW
  orange, UNVERIFIED grey. A reader sees the strength of each claim at a
  glance, which is the whole point of the tagging system.
- **Gaps and contradictions are panels, not footnotes.** They get their own
  tinted blocks so they cannot be skimmed past. The Gaps panel is always
  present.
- **Sources show their tier.** The `T1`–`T8` badges make the credibility
  hierarchy visible, so a "T7 opinion" never reads like a "T1 primary record".
- **The plan is visible.** Surfacing the todos shows the user the question was
  decomposed, not answered with one shallow search.

## Render modes

The live control panel (`static/index.html`) renders results two ways,
switchable in the composer:

1. **Streaming** (default) — consumes the CloudEvents-over-SSE stream from
   `POST /research/stream`, showing live status steps and streaming the
   markdown answer token by token.
2. **A2UI** — consumes [A2UI](https://a2ui.org) surface messages from
   `POST /research/a2ui` and renders them natively via a real A2UI client
   (`static/a2ui-client.js`). The client maintains surfaces and a data model,
   handles `createSurface` / `updateComponents` / `updateDataModel` /
   `deleteSurface`, renders basic-catalog components (Heading, Text, List,
   Divider, Row, Column, Card, Button), resolves `{{path}}` data bindings, and
   surfaces confidence tags as themed chips. It executes no agent-supplied
   code.

## Status

The control panel is functional (both render modes work against the running
service). The standalone HTML in `ui-mockup.html` remains as a static visual
reference of the target layout.
