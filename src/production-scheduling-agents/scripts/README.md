# `scripts/` — run helpers

Operational scripts for this demo. Keep them idempotent and safe to re-run.

## What's here today

| Script | Purpose |
|---|---|
| [`run_demo.py`](run_demo.py) | Run one scripted disruption through the whole loop from the CLI (no UI). Replay mode by default; with `PROJECT_ENDPOINT` set it drives the live Foundry agents; `--record` saves live responses as replay fixtures. `--all` runs every storyline. |

```bash
python scripts/run_demo.py --disruption machine_down
python scripts/run_demo.py --disruption material_delay --choose SCN-A
python scripts/run_demo.py --all
```

## Deployment is Terraform, not scripts

This demo is fully Terraform-driven: `cd infra && terraform apply` provisions
the Azure resources **and** (once the web app lands) ships the application code
via `zip_deploy_file`. There is deliberately no `deploy.ps1` — the manifest's
deploy entrypoint is the Terraform command itself. See
[`../infra/README.md`](../infra/README.md) and
[`../GETTING_STARTED.md`](../GETTING_STARTED.md).

## Rules

- **Idempotent.** Re-running should converge, not duplicate or error.
- **No secrets in scripts.** Read from `.env` / the environment; auth via
  `DefaultAzureCredential`.
- **Print next steps.** Echo what the user should do after a run.
