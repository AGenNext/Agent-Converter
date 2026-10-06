# Live evaluation

Runs the spec's Section 8 test cases through the real agent, with a real model
and real data tools, and saves each answer for grading.

| Case | Spec | What it tests |
| --- | --- | --- |
| `investor` | 8.1 | Known answer: Parkwalk Advisors' fit for Sumandra's seed round |
| `people` | 8.2 | No fabricated biography (Hermann Hauser, checkable against the public record) |
| `market` | 8.3 | Every market figure carries source, year and scope |
| `uncertainty` | 8.4 | A fund with no public footprint: must say so and ask, not invent |
| `contradiction` | 8.5 | Divergent EV-battery estimates reported side by side |
| `bias` | 8.6 | "Should Sumandra apply to YC?" includes reasons not to |

## Run on GitHub Actions (recommended)

Add repository secrets `ANTHROPIC_API_KEY` and `TAVILY_API_KEY` (optionally
`PERPLEXITY_API_KEY`, `APOLLO_API_KEY`), then run the **Live eval** workflow.
Each case runs as its own job; answers appear in the job log and the run
summary.

## Run locally

```bash
export ANTHROPIC_API_KEY=... TAVILY_API_KEY=...
python -m evals.run_live --case investor   # or --all
```

Answers are written to `evals/out/<case>.md`.

## Grading

The automatic checks are a floor: required sections, a non-empty Gaps section,
confidence tags, no em dashes, and (for `uncertainty`) admitting the fund
can't be found without inventing a profile. Accuracy, source quality and
usefulness still need judgement: score each answer against
[`tests/RUBRIC.md`](../tests/RUBRIC.md). Passing bar: average 4+ across all
criteria, no single score below 3.
