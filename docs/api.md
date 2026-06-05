# HTTP API

The agent runs as a FastAPI service (`server.py`). Start it with `make run` (or
`uvicorn server:app --port 8080`) and open:

- **Swagger UI**: `http://localhost:8080/docs`
- **ReDoc**: `http://localhost:8080/redoc`
- **OpenAPI schema**: `http://localhost:8080/openapi.json`

These are generated from the code, so they are always in sync. The control
panel is served at `/`.

## Endpoints

| Method | Path | Tag | Purpose |
| --- | --- | --- | --- |
| POST | `/research` | research | Run research, return the full report |
| POST | `/research/stream` | research | Stream progress as CloudEvents over SSE |
| POST | `/research/a2ui` | research | Stream the result as A2UI surface messages |
| GET | `/healthz` | health | Liveness probe |
| GET | `/readyz` | health | Readiness probe |
| GET | `/api/info` | health | Model + which tools are configured |
| GET | `/` | ui | Control panel |

### POST /research

```bash
curl -s localhost:8080/research \
  -H 'Content-Type: application/json' \
  -d '{"question": "Research Parkwalk Advisors for a UK aerospace seed."}'
```

```json
{ "answer": "## Quick answer\nStrong thematic fit. ..." }
```

### POST /research/stream (CloudEvents over SSE)

Each SSE frame is a structured-mode [CloudEvent](https://github.com/cloudevents/spec).
Event types:

- `io.agennext.research.accepted` — `{ "question" }`
- `io.agennext.research.status` — `{ "step" }` (a pipeline step)
- `io.agennext.research.token` — `{ "text" }` (incremental answer text)
- `io.agennext.research.completed` — `{ "answer" }`
- `io.agennext.research.error` — `{ "message" }`

```bash
curl -N localhost:8080/research/stream \
  -H 'Content-Type: application/json' \
  -d '{"question": "..."}'
```

### POST /research/a2ui (A2UI over SSE)

Streams [A2UI](https://a2ui.org) JSON-RPC messages (`createSurface`,
`updateComponents`, `updateDataModel`) so an A2UI client can render the result
natively. The bundled control panel includes a working client; see
[ui-mockup](ui-mockup.md).

## Errors

Errors use standard HTTP status codes with a JSON `{ "detail": "..." }` body.
`503` means the agent is not ready yet (still building on startup); `422` means
the request body was invalid. Internal failures never leak exception detail to
the client; they are logged server-side and returned as a generic message.

## Other interfaces

- **MCP**: the same agent is exposed over the Model Context Protocol. See
  [mcp.md](mcp.md).
- **CLI**: `python main.py "question"` or `make cli`.
