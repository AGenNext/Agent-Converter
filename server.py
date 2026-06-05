"""HTTP service wrapper for the Research deep agent.

A small FastAPI app so the agent runs as a long-running, Kubernetes-native
service with health and readiness probes, a JSON research endpoint, and a
built-in control panel served at `/`.

Run locally:
    uvicorn server:app --host 0.0.0.0 --port 8080
Then open http://localhost:8080

Endpoints:
    GET  /            the control panel (web dashboard)
    GET  /healthz     liveness  (process is up)
    GET  /readyz      readiness (agent built and ready)
    GET  /api/info    service + tool configuration status (JSON)
    POST /research    {"question": "..."} -> {"answer": "..."}
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from research_agent import build_agent

app = FastAPI(title="Research Deep Agent", version="1.0.0")

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
    _agent = build_agent()
    _ready = True


class ResearchRequest(BaseModel):
    question: str


class ResearchResponse(BaseModel):
    answer: str


@app.get("/healthz")
def healthz() -> dict:
    """Liveness: the process is running."""
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict:
    """Readiness: the agent is built and can serve requests."""
    if not _ready or _agent is None:
        raise HTTPException(status_code=503, detail="agent not ready")
    return {"status": "ready"}


@app.get("/api/info")
def info() -> dict:
    return {
        "name": "Research Deep Agent",
        "version": "1.0.0",
        "model": os.environ.get("RESEARCH_AGENT_MODEL", "anthropic:claude-sonnet-4-5"),
        "ready": _ready,
        "tools": {
            name: bool(os.environ.get(env)) for name, env in _TOOL_KEYS.items()
        },
    }


@app.post("/research", response_model=ResearchResponse)
def research(req: ResearchRequest) -> ResearchResponse:
    if not _ready or _agent is None:
        raise HTTPException(status_code=503, detail="agent not ready")
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="question must not be empty")
    result = _agent.invoke(
        {"messages": [{"role": "user", "content": question}]}
    )
    return ResearchResponse(answer=result["messages"][-1].content)


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


def _research_events(question: str, subject: str):
    yield _cloud_event(
        "io.agennext.research.accepted", {"question": question}, subject
    )
    try:
        inputs = {"messages": [{"role": "user", "content": question}]}
        final = ""
        for mode, chunk in _agent.stream(
            inputs, stream_mode=["updates", "messages"]
        ):
            if mode == "messages":
                msg = chunk[0] if isinstance(chunk, tuple) else chunk
                text = getattr(msg, "content", "")
                if isinstance(text, str) and text:
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
        logger.exception("research stream failed for subject %s", subject)
        yield _cloud_event(
            "io.agennext.research.error",
            {"message": "Research failed. Please try again."},
            subject,
        )


@app.post("/research/a2ui")
def research_a2ui(req: ResearchRequest) -> StreamingResponse:
    """Run research and stream the result as A2UI surface messages over SSE.

    Lets an A2UI-capable client render the output natively. See
    research_agent/a2ui.py and https://a2ui.org.
    """
    if not _ready or _agent is None:
        raise HTTPException(status_code=503, detail="agent not ready")
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="question must not be empty")

    from research_agent.a2ui import render_messages, sse_frames

    def gen():
        try:
            result = _agent.invoke(
                {"messages": [{"role": "user", "content": question}]}
            )
            answer = result["messages"][-1].content
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


@app.post("/research/stream")
def research_stream(req: ResearchRequest) -> StreamingResponse:
    """Stream the agent's progress in real time as CloudEvents over SSE."""
    if not _ready or _agent is None:
        raise HTTPException(status_code=503, detail="agent not ready")
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="question must not be empty")
    subject = str(uuid.uuid4())
    return StreamingResponse(
        _research_events(question, subject),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# Control panel. Mounted last so the API routes above take precedence.
if _STATIC.is_dir():
    @app.get("/")
    def panel() -> FileResponse:
        return FileResponse(_STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=_STATIC), name="static")
