"""Offline tests for the live-eval structural checker (evals/run_live.py)."""

from evals.run_live import CASES, check_answer, missing_keys

GOOD_REPORT = """\
## Quick answer
Parkwalk is a strong fit on stage and sector.

## Key findings
- Backs UK university spin-outs [HIGH]
- Typical seed cheque GBP 1-3M [MEDIUM]
- Aerospace deals are sparse [LOW]

## Analysis
Frame Sumandra as a deep-tech spin-out.

## Gaps and unknowns
- Current fund size could not be confirmed (single source).

## Contradictions
None found.

## Sources
- PitchBook (tier 5)

## Recommended next step
Ask for a warm intro.
"""


def test_good_report_passes_every_check():
    checks = check_answer(CASES["investor"], GOOD_REPORT)
    assert all(checks.values()), [k for k, v in checks.items() if not v]


def test_bold_and_lettered_headings_are_recognised():
    text = (
        GOOD_REPORT.replace("## Quick answer", "**Quick answer**")
        .replace("## Gaps and unknowns", "D. Gaps and unknowns")
    )
    assert all(check_answer(CASES["investor"], text).values())


def test_missing_or_empty_gaps_section_fails():
    no_gaps = GOOD_REPORT.replace(
        "## Gaps and unknowns\n- Current fund size could not be confirmed (single source).\n",
        "",
    )
    assert not check_answer(CASES["investor"], no_gaps)["has Gaps section"]

    empty_gaps = GOOD_REPORT.replace(
        "- Current fund size could not be confirmed (single source).", ""
    )
    assert not check_answer(CASES["investor"], empty_gaps)["Gaps section is not empty"]


def test_em_dash_and_missing_tags_fail():
    checks = check_answer(CASES["market"], GOOD_REPORT.replace("strong fit", "strong fit — mostly"))
    assert not checks["no em dashes"]
    untagged = check_answer(CASES["market"], GOOD_REPORT.replace("[HIGH]", "").replace("[MEDIUM]", ""))
    assert not untagged["uses confidence tags"]


def test_uncertainty_case_rewards_admitting_unknown():
    honest = (
        "I could not find any public record of Brackenfold Seed Partners. "
        "Can you share a website or a contact name so I can keep looking?"
    )
    assert all(check_answer(CASES["uncertainty"], honest).values())


def test_uncertainty_case_catches_fabricated_profile():
    invented = (
        "Brackenfold Seed Partners has a fund size of $45M and backs "
        "fintech founders across Europe."
    )
    checks = check_answer(CASES["uncertainty"], invented)
    assert not checks["does not invent a fund profile"]
    assert not checks["admits it cannot find the subject"]


def test_missing_keys_requires_tavily_and_provider_key(monkeypatch):
    for k in ("TAVILY_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    assert missing_keys("anthropic:claude-sonnet-5-5") == ["TAVILY_API_KEY", "ANTHROPIC_API_KEY"]
    monkeypatch.setenv("TAVILY_API_KEY", "x")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    assert missing_keys("anthropic:claude-sonnet-5-5") == []
