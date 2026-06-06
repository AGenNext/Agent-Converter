"""A2UI (Agent to UI) rendering for research output.

A2UI is an open, declarative protocol for agent-driven interfaces: the agent
emits JSON messages describing a UI "surface" and the client renders it
natively, without executing agent-supplied code. See https://a2ui.org
(protocol v0.9). The server-to-client message types are:

  createSurface     start a new surface
  updateComponents  add or update components on a surface
  updateDataModel   push data into the surface's data model
  deleteSurface     remove a surface

This module converts a finished research answer (markdown text) into a small
A2UI surface using components from the v0.9 "basic" catalog (Heading, Text,
Divider, List). Messages are emitted as JSON-RPC 2.0 notifications, which is
one of A2UI's supported transports (SSE + JSON-RPC).

Note: the exact component property names are validated client-side against the
chosen A2UI catalog. This emitter targets the basic catalog shape; if your
client pins a different catalog version, adjust `_component` accordingly. The
message envelopes (method names, surfaceId/components/dataModel structure) are
the stable part of the protocol.
"""

from __future__ import annotations

import uuid
from typing import Iterable


def _rpc(method: str, params: dict) -> dict:
    return {"jsonrpc": "2.0", "method": method, "params": params}


def _component(comp_id: str, comp_type: str, props: dict) -> dict:
    return {"id": comp_id, "component": {"componentType": comp_type, "properties": props}}


def _answer_to_components(answer: str) -> list[dict]:
    """Map a markdown answer into basic-catalog components.

    Headings (`#`/`##`/`###`) become Heading components, bullet lines collapse
    into a List, blank lines become a Divider between blocks, everything else
    is Text. Confidence tags are surfaced as a `tag` property so a themed
    client can colour them.
    """
    components: list[dict] = []
    n = 0
    bullets: list[str] = []

    def flush_bullets():
        nonlocal n
        if bullets:
            components.append(
                _component(f"c{n}", "List", {"items": list(bullets)})
            )
            n += 1
            bullets.clear()

    for raw in answer.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            flush_bullets()
            continue
        if stripped.startswith(("- ", "* ")):
            bullets.append(stripped[2:].strip())
            continue
        flush_bullets()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            components.append(
                _component(
                    f"c{n}",
                    "Heading",
                    {"text": stripped.lstrip("# ").strip(), "level": min(level, 4)},
                )
            )
        else:
            props = {"text": stripped}
            for tag in ("HIGH", "MEDIUM", "LOW", "UNVERIFIED"):
                if tag in stripped:
                    props["tag"] = tag
                    break
            components.append(_component(f"c{n}", "Text", props))
        n += 1
    flush_bullets()
    return components


def render_messages(answer: str, surface_id: str | None = None) -> list[dict]:
    """Return the ordered A2UI messages that render `answer` as a surface."""
    surface_id = surface_id or f"research-{uuid.uuid4()}"
    components = _answer_to_components(answer)
    return [
        _rpc("createSurface", {"surfaceId": surface_id, "catalog": "basic"}),
        _rpc(
            "updateComponents",
            {"surfaceId": surface_id, "components": components},
        ),
        _rpc(
            "updateDataModel",
            {"surfaceId": surface_id, "dataModel": {"answer": answer}},
        ),
    ]


def sse_frames(messages: Iterable[dict]) -> Iterable[str]:
    """Serialise A2UI messages as SSE frames (one JSON-RPC message per event)."""
    import json

    for msg in messages:
        yield f"event: {msg['method']}\ndata: {json.dumps(msg)}\n\n"
