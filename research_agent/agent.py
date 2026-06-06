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
from research_agent.tenancy import TenantConfig, load_tenant
from research_agent.tools import ALL_TOOLS


# deepagents accepts a "provider:model" string and resolves it via LangChain's
# init_chat_model, so the agent is vendor-neutral. We are local-first: with no
# cloud key configured the agent defaults to a local Ollama model, so it runs
# with zero API keys. Set a cloud key (or RESEARCH_AGENT_MODEL) to use a hosted
# model instead.
CLOUD_DEFAULT_MODEL = "anthropic:claude-sonnet-4-5"
LOCAL_DEFAULT_MODEL = "ollama:tinyllama"

# Cloud providers we recognise by their conventional API-key env var.
_CLOUD_KEYS = {
    "ANTHROPIC_API_KEY": "anthropic:claude-sonnet-4-5",
    "OPENAI_API_KEY": "openai:gpt-4.1-mini",
    "GOOGLE_API_KEY": "google_genai:gemini-2.0-flash",
}


def default_model() -> str:
    """Resolve the default model id (vendor-neutral, local-first).

    Precedence: RESEARCH_AGENT_MODEL > a recognised cloud provider key >
    LOCAL_MODEL > the local Ollama default. Note: small local models may not
    handle the multi-tool agent loop well; for real use point LOCAL_MODEL at a
    tool-capable local model (e.g. ollama:llama3.1) or set a cloud key.
    """
    explicit = os.environ.get("RESEARCH_AGENT_MODEL")
    if explicit:
        return explicit
    for env_key, model in _CLOUD_KEYS.items():
        if os.environ.get(env_key):
            return model
    return os.environ.get("LOCAL_MODEL") or LOCAL_DEFAULT_MODEL


# Backwards-compatible alias.
DEFAULT_MODEL = CLOUD_DEFAULT_MODEL


def _resolve_model(model):
    """Pick the chat model: explicit arg wins, else the resolved default.

    Always returns something concrete so we never hit the deprecated
    `model=None` path.
    """
    return model or default_model()


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


# Per-tenant agent cache. Each tenant gets its own compiled graph (so its model
# choice sticks); credentials are still resolved per request via tenant_scope.
_TENANT_AGENTS: dict[str, object] = {}


def get_tenant_agent(tenant):
    """Return a cached agent for a tenant.

    `tenant` may be a tenant id (str) or a TenantConfig. The tenant's model
    takes precedence over the env default.
    """
    config = tenant if isinstance(tenant, TenantConfig) else load_tenant(tenant)
    cached = _TENANT_AGENTS.get(config.tenant_id)
    if cached is None:
        cached = build_agent(model=config.model)
        _TENANT_AGENTS[config.tenant_id] = cached
    return cached


__all__ = ["build_agent", "get_tenant_agent"]
