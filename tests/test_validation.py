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
