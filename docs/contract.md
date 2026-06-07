# API contract

The Research Deep Agent's external contract, **v1.0.0** (SemVer). The contract
is constant across channels: a client written for one understands the others.
Machine-readable schemas: [`schemas/research.schema.json`](../schemas/research.schema.json).
The live OpenAPI is at `/openapi.json`.

## Stability

- Breaking changes to request/response shapes or event types bump the **major**
  version. Additive, backward-compatible fields bump the **minor**.
- Unknown fields in requests are rejected (`additionalProperties: false`);
  clients should ignore unknown fields in responses and unknown event types.

## Common

- All `POST` endpoints accept an optional `X-Tenant-ID` header (default
  `default`) — see [multi-tenancy](multi-tenancy.md).
- Errors use standard HTTP status codes with a JSON body `{ "detail": string }`.
  `422` = invalid request; `503` = agent not ready. Internal failures never leak
  exception detail; they return a generic message and are logged server-side.

## POST /research

Request (`ResearchRequest`):
```json
{ "question": "Research Parkwalk Advisors for a UK aerospace seed.", "model": null }
```
- `question` (string, required, min length 1).
- `model` (string, optional, ≤100 chars) — `provider:model` override.

Response 200 (`ResearchResponse`):
```json
{ "answer": "## Quick answer\n..." }
```
`answer` is markdown in the mandated order: Quick answer → Key findings (each
with source + confidence tag) → Analysis → Gaps → Contradictions → Sources →
Recommended next step.

## POST /research/stream  (CloudEvents over SSE)

`Content-Type: text/event-stream`. Each SSE frame is one structured-mode
[CloudEvent](https://github.com/cloudevents/spec) (1.0). The SSE `event:` field
equals the CloudEvent `type`. Ordered event types and their `data`:

| `type` | `data` | Meaning |
| --- | --- | --- |
| `io.agennext.research.accepted` | `{ "question" }` | request accepted |
| `io.agennext.research.status` | `{ "step" }` | a pipeline step started |
| `io.agennext.research.token` | `{ "text" }` | incremental answer text |
| `io.agennext.research.completed` | `{ "answer" }` | final answer |
| `io.agennext.research.error` | `{ "message" }` | generic failure |

## POST /research/a2ui  (A2UI over SSE)

Streams [A2UI](https://a2ui.org) server-to-client messages as JSON-RPC 2.0
notifications (one per SSE frame): `createSurface`, `updateComponents`,
`updateDataModel`. The bundled control panel ships a conforming client
(`static/a2ui-client.js`).

## GET /api/info  / GET /healthz / GET /readyz

- `/api/info` (`Info`): `{ name, version, environment, model, ready, tools }`
  where `tools` maps each tool name to whether its key is configured.
- `/healthz` → `{ "status": "ok" }` (liveness).
- `/readyz` → `{ "status": "ready" }` or `503` (readiness).

## MCP

Over the Model Context Protocol (`mcp_server.py`):
- `research(question: string) -> string`
- `research_pack(question: string, pack: string) -> string`
  where `pack` ∈ {investor, people, market, company, technical, sales, general}.

## Invariants (behavioural contract)

Regardless of channel, the agent: triangulates important claims across 2+
sources; tags every factual claim HIGH/MEDIUM/LOW/UNVERIFIED; always includes a
non-empty Gaps section; surfaces contradictions; and degrades a missing or
failed tool to a reported gap, never a fabrication.
