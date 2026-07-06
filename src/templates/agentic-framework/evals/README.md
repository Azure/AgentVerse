# `evals/` — prove the agent works, and keep it working (block #8)

> A prompt tweak is a code change. Evals are how you ship one with confidence: a golden
> dataset of input→expected cases, run by a harness, gated in CI.

## The shape

```
evals/
├── golden_dataset.json    # curated input → expected-outcome cases
├── run_evals.py           # harness: run pipeline per case, assert, write report
└── last_report.json       # generated: per-case detail + aggregate pass rate
```

## Golden dataset — one case

```json
{
  "id": "low_risk_case",
  "input": { "request": "..." },
  "expect": {
    "decision": "approve",
    "severity": "low",
    "security_flag": false
  }
}
```

Include, at minimum:
- a **happy path** case,
- a **boundary** case (just over/under a threshold),
- an **adversarial** case (a prompt-injection attempt — assert `security_flag: true`).

## The harness — what it does

1. Load `golden_dataset.json`.
2. Run the real pipeline (orchestrator → agents) for each case, calling the real model.
3. Assert the result against `expect`.
4. Write `last_report.json` with per-case detail and an aggregate pass rate.
5. Exit non-zero if the pass rate drops below the bar — so CI can block the merge.

```powershell
# run locally
az login
$env:AZURE_OPENAI_ENDPOINT = "https://<your-aoai>.openai.azure.com/"
python -m evals.run_evals
```

## The eval gate (CI)

Wire `run_evals.py` into the demo's `.github/workflows/eval-on-pr.yml` so any PR touching
`agents/**` or `evals/**`:
- runs the suite against the real model,
- posts a markdown table of per-case results on the PR,
- **fails the check** (blocks merge) on regression.

This is the "WOW moment" in the insurance demo: change a compliance threshold → the eval
gate shows the impact on every case → merge is blocked without approval.

## Rules

- **Assert outcomes, not "it ran."** Check the decision/output fields, not just absence of
  errors.
- **Keep the dataset small and sharp** — a handful of discriminating cases beats hundreds of
  redundant ones.
- **Version the dataset with the prompts.** They change together.
