# `scripts/` — deploy & run helpers

Operational scripts for this demo. Keep them idempotent and safe to re-run.

## Suggested scripts

| Script | Purpose |
|---|---|
| `deploy.ps1` / `deploy.sh` | One-command deploy: `terraform apply` (infra) → build/push backend → publish frontend. Print the app + API URLs at the end. |
| `bootstrap_agents.py` | Create the persistent Foundry agents from each `agent.yaml` (idempotent; `--reset` to recreate). |
| `run_demo.py` | Run the workflow once from the CLI (no UI) for smoke testing. |

## Rules

- **Idempotent.** Re-running should converge, not duplicate or error.
- **No secrets in scripts.** Read from `.env` / the environment; auth via
  `DefaultAzureCredential`.
- **Print next steps.** After deploy, echo the URLs and any manual portal step still needed.

> See the insurance demo's `scripts/deploy.ps1` and foundryairlines' `app/scripts/` for
> real examples.
