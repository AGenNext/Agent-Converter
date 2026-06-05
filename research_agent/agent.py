"""Assemble the Research deep agent.

This wires the spec's "brain" (orchestrator instructions), the source-pack
sub-agents and the tools into a single LangChain `deepagents` agent.

Usage:
    from research_agent import build_agent
    agent = build_agent()
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "Research Parkwalk ..."}]}
    )
    print(result["messages"][-1].content)
"""

from __future__ import annotations

import os

from deepagents import create_deep_agent

from research_agent.flags import get_list, is_enabled
from research_agent.prompts import ORCHESTRATOR_INSTRUCTIONS
from research_agent.subagents import ALL_SUBAGENTS
from research_agent.tools import ALL_TOOLS


# Sensible default. deepagents accepts a "provider:model" string and resolves
# it via LangChain's init_chat_model, so no extra wiring is needed.
DEFAULT_MODEL = "anthropic:claude-sonnet-4-5"


def _resolve_model(model):
    """Pick the chat model.

    Precedence: explicit `model` arg > RESEARCH_AGENT_MODEL env var >
    DEFAULT_MODEL. Always returns something concrete so we never hit the
    deprecated `model=None` path.
    """
    return model or os.environ.get("RESEARCH_AGENT_MODEL") or DEFAULT_MODEL


def _select_subagents():
    """Filter the sub-agents using OpenFeature flags.

    - research.enable_critique (default true): include the critique pack.
    - research.enabled_packs (default empty): if non-empty, only research packs
      whose name matches one of the listed tokens are attached. The critique
      pack is governed solely by its own flag.
    """
    enable_critique = is_enabled("research.enable_critique", True)
    only = [t.lower() for t in get_list("research.enabled_packs", [])]

    selected = []
    for sa in ALL_SUBAGENTS:
        name = sa["name"]
        if name == "critique":
            if enable_critique:
                selected.append(sa)
            continue
        if only and not any(tok in name for tok in only):
            continue
        selected.append(sa)
    return selected


def build_agent(model=None):
    """Build and return the compiled Research deep agent graph.

    `model` may be a LangChain chat model or a "provider:model-name" string.
    """
    return create_deep_agent(
        model=_resolve_model(model),
        tools=ALL_TOOLS,
        system_prompt=ORCHESTRATOR_INSTRUCTIONS,
        subagents=_select_subagents(),
    )


__all__ = ["build_agent"]
