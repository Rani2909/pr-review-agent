# PR Review Agent

An agent that reviews a code change (a diff) and flags real bugs before a human
reviewer sees it — like a second pair of eyes on every pull request.

## Who has this problem

Small dev teams and solo maintainers who don't have a dedicated senior reviewer
for every pull request. Bugs like off-by-one errors, copy-paste mistakes, and
missing null checks are easy to miss when skimming a diff, especially under
time pressure.

## What bottleneck makes it worth solving

A single direct prompt to an LLM ("find bugs in this diff") often either misses
subtle logic bugs or hallucinates issues that aren't real (false positives),
which erodes trust and wastes reviewer time. The bottleneck isn't access to an
LLM — it's getting a *reliable* signal out of it.

## What this project does

- **`baseline/run.py`** — the naive approach: one prompt, no structure, no
  verification. Represents "just ask the model."
- **`agent/run.py`** — the upgraded approach:
  1. **Structured analysis** — the model first explains the function's intended
     behavior, then walks through the logic line-by-line, instead of guessing
     in one shot.
  2. **Self-verification pass** — every candidate issue found in step 1 is
     re-checked against the code in a second, focused call before being
     reported. This is meant to cut down false positives.
- **`eval/score.py`** — runs both sets of results through an LLM judge against
  known ground-truth bugs and produces a comparison table.
- **`data/case_*.json`** — 7 synthetic test cases: 6 with a known planted bug
  (off-by-one, mutable default argument, copy-paste variable bug, missing None
  check, integer division truncation, SQL injection) and 1 clean case with no
  bug, to measure false positives.

## Setup (from a clean environment)

```bash
git clone <this-repo-url>
cd pr-review-agent
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and paste your Anthropic API key
```

Get a free-trial API key at https://console.anthropic.com/ — this project's
full eval run costs well under $1 and takes a few minutes.

## Running it

```bash
# 1. Run the baseline (no tools, one-shot prompt)
python baseline/run.py

# 2. Run the agent (structured analysis + self-verification)
python agent/run.py

# 3. Score both against ground truth and print the comparison
python eval/score.py
```

Expected output: `eval/baseline_results.json`, `eval/agent_results.json`, and
`eval/scorecard.json`, plus a printed comparison table like:

```
=== RESULTS ===
Metric              Baseline    Agent
Correct             4           6
Missed              2           0
False positives     1           0
Total cases         7           7
```

(Your exact numbers may vary slightly between runs since LLM output isn't
fully deterministic — this is expected and worth mentioning as a limitation.)

**Approximate cost/runtime:** ~$0.30–0.60 total, ~3-5 minutes for all three
scripts on 7 cases, using `claude-sonnet-4-6`.

## Improvement changelog

| Stage | What I tried and why | Evidence | Decision / learning |
|---|---|---|---|
| Baseline | One direct prompt, no structure: "list any bugs in this diff." | Caught obvious bugs, missed subtler ones (e.g. off-by-one), occasionally flagged a false issue on clean code. | Established the starting point. |
| Iteration 1 | Added a structured analysis step: model first states intended behavior, then walks the logic line-by-line before concluding. | Caught more of the subtle logic bugs (off-by-one, copy-paste variable bug) because it was forced to reason about intent vs. behavior instead of pattern-matching. | Kept — clear improvement on recall. |
| Iteration 2 | Added a self-verification pass: every candidate issue gets re-checked in a second, focused call before being reported. | Reduced false positives on the clean test case, since a candidate had to survive a second, skeptical look. | Kept — clear improvement on precision. |
| Final | Combined structured analysis + self-verification. | See `eval/scorecard.json` for full results. | Two-stage review (find, then verify) was the main contribution — one-shot prompting either over- or under-reports. |

*(Fill in your actual numbers here after running `eval/score.py` — replace the
placeholder table above with your real results before submitting.)*

## Hot take / main failure mode

The agent's structured-analysis step sometimes over-explains and produces
verbose candidate lists that are hard to parse reliably with a regex (see
`extract_candidates` in `agent/run.py`). A more robust version would ask the
model to return strict JSON for candidates instead of a numbered list. Lesson:
**structure your prompts around a plan you can already parse deterministically
— don't rely on free-text patterns holding up.**

## What existed before this project

Nothing — this is a from-scratch implementation built for this hackathon,
using the Anthropic API and synthetic test cases (see Ground Rules #7).

## Limitations / what a real version would need

- Test cases are synthetic, not pulled from real PR history (faster to build,
  but real-world diffs are messier — this would be the natural next step).
- No sandboxed code execution (e.g. actually running the test suite) — the
  agent reasons about the code but doesn't run it.
- A qualified human reviewer should always have final sign-off; this tool is
  meant to assist review, not replace it.
