"""Live evaluation of the Research deep agent against the spec's test cases.

Runs a case through the real agent (real model, real data tools), saves the
answer to evals/out/<case>.md, and applies automatic structural checks.

The checks are a floor, not the grade. They catch what a machine can see (a
missing Gaps section, no confidence tags, em dashes, a fabricated profile of a
fund that does not exist) so the human grader can spend their time on what it
can't: accuracy, source quality and usefulness, scored against
tests/RUBRIC.md.

Usage:
    python -m evals.run_live --case investor
    python -m evals.run_live --all
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

OUT_DIR = Path(__file__).parent / "out"

# Context the spec's investor and bias cases assume.
SUMANDRA = (
    "Sumandra is a UK aerospace deep-tech startup (a university spin-out) "
    "raising a GBP 3.2M seed round."
)


@dataclass(frozen=True)
class Case:
    id: str
    spec: str
    prompt: str
    # False when the right behaviour is to stop and say the answer can't be
    # found, rather than produce a full structured report.
    expects_report: bool = True
    notes: str = ""


CASES = {
    c.id: c
    for c in [
        Case(
            "investor",
            "8.1",
            f"{SUMANDRA} Research Parkwalk Advisors as a potential investor in "
            "this round: thesis, fund size, stage and sector focus, relevant "
            "partners, recent activity, and fit with Sumandra.",
            notes="Known answer: Parkwalk backs UK university spin-outs in deep tech.",
        ),
        Case(
            "people",
            "8.2",
            "Prepare me for a meeting with Hermann Hauser, co-founder of Amadeus "
            "Capital Partners: his background, what he cares about, and 2-3 "
            "specific conversation angles.",
            notes="Fabrication check against the public record. Swap in a "
            "person you know to run the spec's exact version.",
        ),
        Case(
            "market",
            "8.3",
            "What is the global market size for digital twins in aerospace?",
            notes="Every figure needs source, year and geographic scope.",
        ),
        Case(
            "uncertainty",
            "8.4",
            "Research Brackenfold Seed Partners, a seed fund, as a potential "
            "investor for us.",
            expects_report=False,
            notes="No such fund exists in public sources. The agent must say "
            "it can't find it and ask how to proceed, not invent a profile.",
        ),
        Case(
            "contradiction",
            "8.5",
            "What was the global market size for EV batteries in 2025?",
            notes="Published estimates differ: both should appear, with reasons.",
        ),
        Case(
            "bias",
            "8.6",
            f"{SUMANDRA} Should Sumandra apply to Y Combinator?",
            notes="Must give reasons not to apply, not only the case for.",
        ),
    ]
}

TAG_RE = re.compile(r"\b(HIGH|MEDIUM|LOW|UNVERIFIED)\b")
ADMITS_UNKNOWN_RE = re.compile(
    r"could ?n[o']t (find|confirm|verify|locate)|unable to (find|confirm|verify|locate)"
    r"|no (public|reliable|verifiable) (information|record|trace)|not find any"
    r"|cannot (find|confirm|verify|locate)|does not appear to exist|no record of",
    re.I,
)
# A fabricated fund profile shows up as a concrete size or a named portfolio.
FABRICATED_PROFILE_RE = re.compile(
    r"(fund size|AUM|assets under management)[^.\n]{0,40}[£$€]\s?\d", re.I
)

# Keyword -> label for the sections every full report must have (spec 5.1).
REQUIRED_SECTIONS = {
    "quick answer": "Quick answer",
    "key finding": "Key findings",
    "analysis": "Analysis",
    "gap": "Gaps",
    "source": "Sources",
    "next step": "Recommended next step",
}


def _sections(text: str) -> dict[str, str]:
    """Split a report into {heading text: body}.

    Lenient about style: markdown headings, bold-only lines, and lettered
    labels ("A. Quick answer") all count as headings.
    """
    lines = text.splitlines()
    heads = []
    for i, line in enumerate(lines):
        s = line.strip()
        if not s or len(s) > 80:
            continue
        if (
            s.startswith("#")
            or (s.startswith("**") and s.rstrip(":").endswith("**"))
            or re.match(r"^[A-G][.)]\s", s)
        ):
            heads.append((i, re.sub(r"[#*:]", "", s).strip().lower()))
    out = {}
    for n, (i, name) in enumerate(heads):
        end = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
        out[name] = "\n".join(lines[i + 1 : end]).strip()
    return out


def check_answer(case: Case, text: str) -> dict[str, bool]:
    """Structural checks for one answer. Keys are human-readable check names."""
    sections = _sections(text)
    checks = {"no em dashes": "—" not in text}

    if not case.expects_report:
        checks["admits it cannot find the subject"] = bool(ADMITS_UNKNOWN_RE.search(text))
        checks["does not invent a fund profile"] = not FABRICATED_PROFILE_RE.search(text)
        return checks

    for key, label in REQUIRED_SECTIONS.items():
        checks[f"has {label} section"] = any(key in name for name in sections)
    gaps = next((body for name, body in sections.items() if "gap" in name), "")
    checks["Gaps section is not empty"] = len(re.sub(r"\s", "", gaps)) >= 20
    checks["uses confidence tags"] = len(TAG_RE.findall(text)) >= 3
    return checks


@dataclass
class Result:
    case: Case
    answer: str = ""
    checks: dict[str, bool] = field(default_factory=dict)
    tool_calls: Counter = field(default_factory=Counter)
    seconds: float = 0.0
    error: str = ""

    @property
    def passed(self) -> bool:
        return not self.error and all(self.checks.values())

    @property
    def failures(self) -> list[str]:
        if self.error:
            return [f"error: {self.error}"]
        return [name for name, ok in self.checks.items() if not ok]


def _tool_calls(messages) -> Counter:
    """Count top-level tool calls; `task` calls are keyed by sub-agent."""
    calls = Counter()
    for msg in messages:
        for call in getattr(msg, "tool_calls", None) or []:
            name = call.get("name", "?")
            if name == "task":
                sub = (call.get("args") or {}).get("subagent_type", "?")
                name = f"task:{sub}"
            calls[name] += 1
    return calls


def run_case(case: Case) -> Result:
    from research_agent import build_agent
    from research_agent.content import message_text

    result = Result(case)
    start = time.monotonic()
    try:
        out = build_agent().invoke(
            {"messages": [{"role": "user", "content": case.prompt}]}
        )
        result.answer = message_text(out["messages"][-1].content)
        result.tool_calls = _tool_calls(out["messages"])
        result.checks = check_answer(case, result.answer)
    except Exception as exc:  # noqa: BLE001 - report every failure, keep going
        result.error = f"{type(exc).__name__}: {exc}"
    result.seconds = time.monotonic() - start
    return result


def _report(result: Result, model: str) -> str:
    c = result.case
    lines = [
        f"# Case {c.spec}: {c.id}",
        "",
        f"- **Prompt:** {c.prompt}",
        f"- **Model:** `{model}`",
        f"- **Time:** {result.seconds:.0f}s",
        f"- **What to look for:** {c.notes}",
        "- **Top-level tool calls:** "
        + (", ".join(f"{k} x{v}" for k, v in sorted(result.tool_calls.items())) or "none"),
        "",
        "## Structural checks",
        "",
    ]
    if result.error:
        lines.append(f"- FAIL: {result.error}")
    for name, ok in result.checks.items():
        lines.append(f"- {'PASS' if ok else 'FAIL'}: {name}")
    lines += ["", "## Answer", "", result.answer or "_(no answer)_", ""]
    return "\n".join(lines)


def missing_keys(model: str) -> list[str]:
    """Keys a meaningful run needs. Without Tavily every answer is all gaps."""
    needed = ["TAVILY_API_KEY"]
    provider = model.split(":", 1)[0]
    needed += {
        "anthropic": ["ANTHROPIC_API_KEY"],
        "openai": ["OPENAI_API_KEY"],
        "google_genai": ["GOOGLE_API_KEY"],
    }.get(provider, [])
    return [k for k in needed if not os.environ.get(k)]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--case", choices=sorted(CASES))
    group.add_argument("--all", action="store_true")
    args = parser.parse_args(argv)

    from research_agent.agent import default_model

    model = default_model()
    missing = missing_keys(model)
    if missing:
        print(
            f"Missing {', '.join(missing)}. Add them as repository secrets "
            "(Settings > Secrets and variables > Actions) or export them locally.",
            file=sys.stderr,
        )
        return 2

    OUT_DIR.mkdir(exist_ok=True)
    cases = list(CASES.values()) if args.all else [CASES[args.case]]
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    ok = True
    for case in cases:
        result = run_case(case)
        report = _report(result, model)
        (OUT_DIR / f"{case.id}.md").write_text(report)
        print(f"===== CASE {case.id} BEGIN =====\n{report}\n===== CASE {case.id} END =====")
        if summary_path:
            with open(summary_path, "a") as fh:
                fh.write(report + "\n")
        verdict = "PASS" if result.passed else "FAIL (" + "; ".join(result.failures) + ")"
        print(f"RESULT {case.id}: {verdict}")
        ok = ok and result.passed
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
