"""HTTP service wrapper for the Research deep agent.

A small FastAPI app so the agent runs as a long-running, Kubernetes-native
service with health and readiness probes, a JSON research endpoint, and a
built-in control panel served at `/`.

Run locally:
    uvicorn server:app --host 0.0.0.0 --port 8080
Then open http://localhost:8080

Endpoints:
    GET  /                the control panel (web dashboard)
    GET  /healthz         liveness  (process is up)
    GET  /readyz          readiness (agent built and ready)
    GET  /api/info        service + tool configuration status (JSON)
    POST /research        {"question": "..."} -> {"answer": "..."}
    POST /research/stream progress as CloudEvents over SSE
    POST /research/a2ui   the result as A2UI surface messages over SSE

All POST endpoints accept an optional `X-Tenant-ID` header for multi-tenancy.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from research_agent.agent import default_model, get_agent
from research_agent.content import message_text
from research_agent.tenancy import (
    DEFAULT_TENANT,
    current_tenant_id,
    load_tenant,
    tenant_scope,
)

_API_DESCRIPTION = """
HTTP API for the Research Deep Agent: an honest, well-sourced, confidence-tagged
research agent.

- `POST /research` returns the full report in one response.
- `POST /research/stream` streams progress in real time as CloudEvents over SSE.
- `POST /research/a2ui` streams the result as A2UI surface messages.
- `GET /healthz` / `GET /readyz` are the liveness / readiness probes.
- `GET /api/info` reports the model and which tools are configured.

Interactive docs: `/docs` (Swagger UI) and `/redoc` (ReDoc).
The machine-readable schema is at `/openapi.json`.
"""

_TAGS_METADATA = [
    {"name": "research", "description": "Run the research agent."},
    {"name": "health", "description": "Liveness, readiness and service info."},
    {"name": "ui", "description": "The bundled control panel."},
]

app = FastAPI(
    title="Research Deep Agent",
    version="1.0.0",
    description=_API_DESCRIPTION,
    openapi_tags=_TAGS_METADATA,
    contact={"name": "AGenNext", "url": "https://github.com/AGenNext/Agent-Converter"},
    license_info={"name": "MIT"},
)

logger = logging.getLogger("research_agent.server")

_STATIC = Path(__file__).parent / "static"

# Built lazily on startup so liveness can pass even if model construction is
# slow, and readiness flips only once the agent is actually ready.
_agent = None
_ready = False

# Which env var powers each tool, for the panel's status display.
_TOOL_KEYS = {
    "tavily": "TAVILY_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
    "apollo": "APOLLO_API_KEY",
    "pitchbook": "PITCHBOOK_API_KEY",
    "factset": "FACTSET_API_KEY",
    "harmonic": "HARMONIC_API_KEY",
    "clay": "CLAY_API_KEY",
}


@app.on_event("startup")
def _startup() -> None:
    global _agent, _ready
    # Warm the default tenant's agent so readiness reflects a real build.
    _agent = get_agent(DEFAULT_TENANT)
    _ready = True


class ResearchRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        description="The research question in natural language. Name the "
        "subject and the decision it informs for the best result.",
        examples=[
            "Research Parkwalk Advisors for a UK aerospace deep-tech seed round."
        ],
    )
    model: str | None = Field(
        default=None,
        max_length=100,
        description="Optional model override, 'provider:model' format. Falls "
        "back to the tenant / server default when omitted.",
    )


class ResearchResponse(BaseModel):
    answer: str = Field(
        ..., description="The structured research report in markdown."
    )


@app.get("/healthz", tags=["health"])
def healthz() -> dict:
    """Liveness: the process is running."""
    return {"status": "ok"}


@app.get("/readyz", tags=["health"])
def readyz() -> dict:
    """Readiness: the agent is built and can serve requests."""
    if not _ready or _agent is None:
        raise HTTPException(status_code=503, detail="agent not ready")
    return {"status": "ready"}


@app.get("/api/info", tags=["health"])
def info() -> dict:
    return {
        "name": "Research Deep Agent",
        "version": "1.0.0",
        "model": default_model(),
        "ready": _ready,
        "tools": {
            name: bool(os.environ.get(env)) for name, env in _TOOL_KEYS.items()
        },
    }


def _tenant_header(x_tenant_id: str | None) -> str:
    return x_tenant_id or DEFAULT_TENANT


@app.post("/research", response_model=ResearchResponse, tags=["research"],
          summary="Run research and return the full report")
def research(
    req: ResearchRequest,
    x_tenant_id: str = Header(default=DEFAULT_TENANT, alias="X-Tenant-ID"),
) -> ResearchResponse:
    if not _ready:
        raise HTTPException(status_code=503, detail="agent not ready")
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="question must not be empty")
    config = load_tenant(_tenant_header(x_tenant_id))
    agent = get_agent(config, req.model)
    with tenant_scope(config):
        result = agent.invoke(
            {"messages": [{"role": "user", "content": question}]}
        )
    return ResearchResponse(answer=message_text(result["messages"][-1].content))


# --- Real-time streaming as CloudEvents over SSE ---------------------------
# https://github.com/cloudevents/spec  (structured content mode, JSON format)

_CE_SOURCE = "/research-deep-agent"


def _cloud_event(ce_type: str, data, subject: str) -> str:
    """Serialise one structured-mode CloudEvent as an SSE frame.

    The SSE `event:` field carries the CloudEvent `type`; the `data:` field
    carries the full JSON-formatted CloudEvent envelope.
    """
    event = {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": _CE_SOURCE,
        "type": ce_type,
        "subject": subject,
        "time": datetime.now(timezone.utc).isoformat(),
        "datacontenttype": "application/json",
        "data": data,
    }
    return f"event: {ce_type}\ndata: {json.dumps(event)}\n\n"


def _research_events(question: str, subject: str, agent, config):
    yield _cloud_event(
        "io.agennext.research.accepted", {"question": question}, subject
    )
    try:
        inputs = {"messages": [{"role": "user", "content": question}]}
        final = ""
        # Enter the tenant scope inside the generator so credentials are bound
        # on the thread that actually iterates the stream.
        with tenant_scope(config):
            for mode, chunk in agent.stream(
                inputs, stream_mode=["updates", "messages"]
            ):
                if mode == "messages":
                    msg = chunk[0] if isinstance(chunk, tuple) else chunk
                    text = message_text(getattr(msg, "content", ""))
                    if text:
                        final += text
                        yield _cloud_event(
                            "io.agennext.research.token", {"text": text}, subject
                        )
                elif mode == "updates" and isinstance(chunk, dict):
                    for node in chunk:
                        yield _cloud_event(
                            "io.agennext.research.status", {"step": node}, subject
                        )
        yield _cloud_event(
            "io.agennext.research.completed", {"answer": final}, subject
        )
    except Exception:  # noqa: BLE001
        # Log the detail server-side; never expose exception text to the client.
        logger.exception(
            "research stream failed (tenant=%s subject=%s)",
            current_tenant_id(), subject,
        )
        yield _cloud_event(
            "io.agennext.research.error",
            {"message": "Research failed. Please try again."},
            subject,
        )


@app.post("/research/a2ui", tags=["research"],
          summary="Stream the result as A2UI surface messages")
def research_a2ui(
    req: ResearchRequest,
    x_tenant_id: str = Header(default=DEFAULT_TENANT, alias="X-Tenant-ID"),
) -> StreamingResponse:
    """Run research and stream the result as A2UI surface messages over SSE.

    Lets an A2UI-capable client render the output natively. See
    research_agent/a2ui.py and https://a2ui.org.
    """
    if not _ready:
        raise HTTPException(status_code=503, detail="agent not ready")
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="question must not be empty")
    config = load_tenant(_tenant_header(x_tenant_id))
    agent = get_agent(config, req.model)

    from research_agent.a2ui import render_messages, sse_frames

    def gen():
        try:
            with tenant_scope(config):
                result = agent.invoke(
                    {"messages": [{"role": "user", "content": question}]}
                )
            answer = message_text(result["messages"][-1].content)
            yield from sse_frames(render_messages(answer))
        except Exception:  # noqa: BLE001
            logger.exception("a2ui research failed")
            yield from sse_frames(
                [{"jsonrpc": "2.0", "method": "updateComponents", "params": {
                    "surfaceId": "error",
                    "components": [{"id": "e0", "component": {
                        "componentType": "Text",
                        "properties": {"text": "Research failed. Please try again."},
                    }}],
                }}]
            )

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/research/stream", tags=["research"],
          summary="Stream progress as CloudEvents over SSE")
def research_stream(
    req: ResearchRequest,
    x_tenant_id: str = Header(default=DEFAULT_TENANT, alias="X-Tenant-ID"),
) -> StreamingResponse:
    """Stream the agent's progress in real time as CloudEvents over SSE."""
    if not _ready:
        raise HTTPException(status_code=503, detail="agent not ready")
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="question must not be empty")
    config = load_tenant(_tenant_header(x_tenant_id))
    agent = get_agent(config, req.model)
    subject = str(uuid.uuid4())
    return StreamingResponse(
        _research_events(question, subject, agent, config),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# Control panel. Mounted last so the API routes above take precedence.
# Redirect "/" to the static-mounted index so the panel's relative asset refs
# (e.g. a2ui-client.js) resolve the same way here as on a static host.
if _STATIC.is_dir():
    @app.get("/", tags=["ui"], include_in_schema=False)
    def panel() -> RedirectResponse:
        return RedirectResponse(url="/static/index.html")

    app.mount("/static", StaticFiles(directory=_STATIC), name="static")
