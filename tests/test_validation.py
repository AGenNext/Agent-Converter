"""Validation scaffolding for the Research deep agent.

Two layers:

1. Structural tests (run offline, no API keys): assert the agent assembles,
   every sub-agent has the required shape, and the orchestrator prompt encodes
   the non-negotiable rules from the spec. These run in CI.

2. Live test-case prompts (Section 8 of the spec). These need API keys and a
   human grader, so they are skipped by default. Set RUN_LIVE_TESTS=1 to print
   each agent output for manual scoring against the rubric in
   `tests/RUBRIC.md`.
"""

import os

import pytest

from research_agent.prompts import ORCHESTRATOR_INSTRUCTIONS
from research_agent.subagents import ALL_SUBAGENTS
from research_agent.tools import ALL_TOOLS


# --- Layer 1: structural tests (offline) -----------------------------------


def test_orchestrator_encodes_core_rules():
    text = ORCHESTRATOR_INSTRUCTIONS.lower()
    for must_have in [
        "stop and ask",  # uncertainty handling
        "never fabricate",  # anti-pattern
        "triangulat",  # 2+ sources
        "confidence tag",  # tagging
        "gaps",  # mandatory gaps section
        "quick answer",  # output structure
    ]:
        assert must_have in text, f"orchestrator prompt missing: {must_have!r}"


def test_every_subagent_has_required_shape():
    seen = set()
    registered = {t.name for t in ALL_TOOLS}
    for sa in ALL_SUBAGENTS:
        assert sa["name"] and sa["name"] not in seen
        seen.add(sa["name"])
        assert sa["description"].strip()
        assert len(sa["system_prompt"]) > 200
        # tool allow-lists must reference real registered tool objects
        for t in sa.get("tools", []):
            assert t.name in registered, (
                f"{sa['name']} references unknown tool {t!r}"
            )


def test_expected_packs_present():
    names = {sa["name"] for sa in ALL_SUBAGENTS}
    assert {
        "investor-research",
        "people-research",
        "market-research",
        "company-research",
        "technical-research",
        "sales-research",
        "general-research",
        "critique",
    } <= names


def test_agent_builds():
    # Importing build_agent and constructing it should not require network.
    from research_agent import build_agent

    agent = build_agent()
    assert agent is not None


def test_default_model_is_local_first(monkeypatch):
    from research_agent.agent import default_model

    for var in ("RESEARCH_AGENT_MODEL", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
                "GOOGLE_API_KEY", "LOCAL_MODEL"):
        monkeypatch.delenv(var, raising=False)

    # No keys at all -> local Ollama default (zero-config local run).
    assert default_model().startswith("ollama:")

    # A recognised cloud key flips the default to that provider.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    assert default_model().startswith("anthropic:")

    # An explicit model id always wins.
    monkeypatch.setenv("RESEARCH_AGENT_MODEL", "openai:gpt-4.1-mini")
    assert default_model() == "openai:gpt-4.1-mini"


def test_message_text_flattens_content():
    from research_agent.content import message_text

    assert message_text("hello") == "hello"
    assert message_text("") == ""
    # Anthropic-style list of content blocks.
    blocks = [
        {"type": "text", "text": "part one "},
        {"type": "tool_use", "name": "x"},  # non-text block ignored
        {"type": "text", "text": "part two"},
    ]
    assert message_text(blocks) == "part one part two"
    assert message_text(None) == ""


def test_a2ui_render_messages():
    from research_agent.a2ui import render_messages

    msgs = render_messages("# Quick answer\nStrong fit [HIGH]\n\n- gap one\n- gap two")
    assert [m["method"] for m in msgs] == [
        "createSurface",
        "updateComponents",
        "updateDataModel",
    ]
    comps = msgs[1]["params"]["components"]
    types = [c["component"]["componentType"] for c in comps]
    assert "Heading" in types and "List" in types
    # Confidence tag is surfaced for themed rendering.
    assert any(
        c["component"]["properties"].get("tag") == "HIGH" for c in comps
    )


def test_tenancy_credential_isolation(monkeypatch):
    from research_agent.tenancy import (
        TenantConfig,
        get_credential,
        load_tenant,
        tenant_scope,
    )

    # Falls back to the process env outside any tenant scope.
    monkeypatch.setenv("TAVILY_API_KEY", "global-key")
    assert get_credential("TAVILY_API_KEY") == "global-key"

    # Inside a tenant scope, the tenant's key wins and does not leak out.
    acme = TenantConfig(tenant_id="acme", keys={"TAVILY_API_KEY": "acme-key"})
    with tenant_scope(acme):
        assert get_credential("TAVILY_API_KEY") == "acme-key"
    assert get_credential("TAVILY_API_KEY") == "global-key"

    # Per-tenant env vars are picked up by load_tenant.
    monkeypatch.setenv("TENANT_BETA_TAVILY_API_KEY", "beta-key")
    monkeypatch.setenv("TENANT_BETA_MODEL", "anthropic:claude-haiku-4-5-20251001")
    cfg = load_tenant("beta")
    assert cfg.keys.get("TAVILY_API_KEY") == "beta-key"
    assert cfg.model == "anthropic:claude-haiku-4-5-20251001"


def test_flags_toggle_subagents(monkeypatch):
    from research_agent import agent as agent_mod

    # Critique on by default.
    names = {sa["name"] for sa in agent_mod._select_subagents()}
    assert "critique" in names
    assert "investor-research" in names

    # Disable critique and restrict to one pack.
    monkeypatch.setenv("OF_RESEARCH_ENABLE_CRITIQUE", "false")
    monkeypatch.setenv("OF_RESEARCH_ENABLED_PACKS", "investor")
    names = {sa["name"] for sa in agent_mod._select_subagents()}
    assert "critique" not in names
    assert names == {"investor-research"}


# --- Layer 2: live spec test cases (manual grading) ------------------------

LIVE_CASES = {
    "investor": "Research Parkwalk Advisors for Sumandra's GBP 3.2M seed round.",
    "people": "Prepare me for a meeting with a named investor you can verify.",
    "market": "What is the global market size for digital twins in aerospace?",
    "uncertainty": "Research a very small, obscure fund with little public info.",
    "contradiction": "What is the global market size for the EV battery market?",
    "bias": "Should Sumandra apply to Y Combinator?",
}


@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_TESTS") != "1",
    reason="set RUN_LIVE_TESTS=1 (and provide API keys) to run live cases",
)
@pytest.mark.parametrize("case", list(LIVE_CASES))
def test_live_case_prints_output(case):
    from research_agent import build_agent

    agent = build_agent()
    out = agent.invoke(
        {"messages": [{"role": "user", "content": LIVE_CASES[case]}]}
    )
    text = out["messages"][-1].content
    print(f"\n===== {case} =====\n{text}\n")
    # Cheap structural guardrail; real grading is manual against the rubric.
    assert "gap" in text.lower(), "output must contain a Gaps section"
