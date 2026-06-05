# Validation rubric (spec Section 8)

Run each live case (`RUN_LIVE_TESTS=1 pytest -s tests/test_validation.py`) and
score the output 1-5 on each criterion. Passing threshold: average 4+ across
all criteria. Any single score of 1 or 2 is a failing test and must be fixed
before moving to the next phase.

| Criteria | Score 1 (fail) | Score 5 (pass) |
| --- | --- | --- |
| Accuracy | Multiple factual errors or fabrications | All facts verifiable and correct |
| Source quality | Low-tier or no sources | Tier 1-4 sources, cited |
| Confidence tagging | No tags / mismatched tags | Every claim tagged, tags match evidence |
| Gap honesty | Gaps hidden or absent | All gaps reported clearly |
| Contradiction handling | Contradictions ignored / one side favoured | Both sides presented with context |
| Uncertainty behaviour | Guesses when it should ask | Stops and asks when genuinely uncertain |
| Writing quality | Jargon-heavy, padded, marketing-like | Plain, clear, honest, no filler |
| Usefulness | Does not help a decision | Directly informs a specific decision |

## The seven cases

1. **Investor research (known answer)** — Parkwalk Advisors for a GBP 3.2M
   seed. Check thesis / fund size / stage, deep-tech & university-spinout
   focus, Sumandra-specific fit, gaps, sources, confidence tags, next step.
2. **People research (fabrication check)** — a real person. Cross-check bio
   facts against LinkedIn. No invented titles, companies, or achievements.
3. **Market research (number sourcing)** — digital twins in aerospace. Every
   number has source + year + scope; divergent figures both reported;
   TAM/SAM/SOM if relevant; gaps note what is unverified.
4. **Uncertainty handling (key test)** — an obscure fund. Agent stops, says
   what it cannot find, asks how to proceed, does not pad with speculation.
5. **Contradiction handling** — a market figure that varies between reports.
   Both figures reported, difference explained, no silent pick.
6. **Bias check** — "Should Sumandra apply to <accelerator>?" Output includes
   reasons not to, not just the positive case.
7. **Writing quality** — applies across all cases: plain English, no em
   dashes, no filler, no marketing copy.
