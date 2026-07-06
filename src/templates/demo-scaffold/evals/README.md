# `evals/` — the eval gate for this demo

Golden-dataset regression suite. Build it following the blueprint:
**[`../../templates/agentic-framework/evals/`](../../templates/agentic-framework/evals/)**.

## Files

```
evals/
├── golden_dataset.json    # input → expected-outcome cases (incl. one adversarial)
├── run_evals.py           # runs the pipeline per case, asserts, writes last_report.json
└── last_report.json       # generated
```

## Run locally

```powershell
az login
$env:AZURE_OPENAI_ENDPOINT = "https://<your-aoai>.openai.azure.com/"
python -m evals.run_evals
```

## Wired into CI

[`../.github/workflows/eval-on-pr.yml`](../.github/workflows/eval-on-pr.yml) runs this on any
PR touching `agents/**` or `evals/**`, comments a per-case table on the PR, and **blocks the
merge** on regression.

## Minimum bar

At least three cases: a happy path, a boundary case, and a prompt-injection case that asserts
the agent flags it. Assert **outcomes** (decision/output fields), not just "it ran."
