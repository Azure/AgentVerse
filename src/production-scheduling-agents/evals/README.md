# `evals/` — the eval gate for this demo

Golden-dataset regression suite, built following the blueprint in
[`../../templates/agentic-framework/evals/`](../../templates/agentic-framework/evals/).

## Files

```
evals/
├── golden_dataset.json    # 4 disruption cases: 2 auto-reschedule, 1 escalation, 1 adversarial
├── run_evals.py           # runs each case through the FULL pipeline, asserts the DECISION
└── last_report.json       # generated
```

Each case runs the whole loop (monitor -> simulator -> orchestrator ->
dispatcher) against a fresh mock plant, so a regression anywhere in the chain —
prompts, fixtures, feasibility checker, policy gate — fails the gate.

## Run locally

```powershell
# Replay mode (default — zero Azure): responses come from agents/fixtures/.
python -m evals.run_evals

# Live mode: exercises the real Foundry agents instead.
az login
$env:PROJECT_ENDPOINT = "https://<account>.services.ai.azure.com/api/projects/<project>"
python -m evals.run_evals
```

## What each case asserts

Outcomes, not "it ran": the orchestrator's `decision`, `escalated`, and
`security_flag` fields, the chosen scenario's `hard_constraint_violations`, and
(for escalations) a minimum number of options presented to the planner. The
prompt-injection case additionally asserts `schedule_changed: false`.

## Wired into CI

[`../.github/workflows/eval-on-pr.yml`](../.github/workflows/eval-on-pr.yml) runs this on any
PR touching `agents/**` or `evals/**`, comments a per-case table on the PR, and **blocks the
merge** on regression.
