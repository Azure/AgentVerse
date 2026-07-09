# Changelog

All notable changes to the production-scheduling demo. Dates are YYYY-MM-DD.

## 2026-07-09 — First full end-to-end verification (stages 1–4 live)

The entire GETTING_STARTED ladder was executed for the first time against a real
Azure subscription. Stages 1–4 and the local dashboard are verified working;
stage 5 is blocked only by subscription-level App Service quota. Everything
below was found — and fixed — during that walkthrough.

### Verified working

- **Stage 1 (replay CLI):** all four scripted disruptions behave exactly as
  documented — `machine_down` auto-reschedules ORD-7712 from CNC-102 to CNC-104
  (confidence 0.92), `material_delay` escalates with three options and
  `--choose SCN-A` applies it, `prompt_injection` rejects at confidence 1.00 with
  the schedule untouched, `rush_order` auto-slots ORD-9105-RUSH onto PRESS-201.
  Misuse is handled: an unknown `--choose` id reports "nothing applied"; an
  unknown disruption key on the API returns 404 listing the valid options.
- **Eval gate:** `python -m evals.run_evals` — 4/4 pass, both before and after
  fixtures were re-recorded from live runs.
- **Local dashboard (bonus stage):** `GET /` serves the frontend; `GET
  /api/run/{key}` streams the full agent pipeline over SSE; `POST /api/choose`
  applied SCN-C and advanced the schedule to v3 with KPI counters tracking
  correctly; `POST /api/reset` restored v1 with zeroed counters.
- **Stage 3 (Terraform):** resource group, Foundry (AIServices S0) account,
  both model deployments, Log Analytics, and Application Insights applied
  cleanly (after the model-version fix below).
- **Stage 4 (live Foundry agents):** all four disruptions produced the correct
  decision class with real gpt-5.1/gpt-5.4 calls — auto_reschedule 0.90,
  escalate_to_planner 0.60, reject 1.00, auto_reschedule 0.86. Replay fixtures
  were re-recorded from these runs (`--all --record`), so offline replays now
  show genuine model output.

### Fixed

- **`agents/shared/foundry.py` — live path updated to the current SDK.**
  `azure-ai-projects` 2.x (installed: 2.3.0) replaced its `.agents` property
  surface with a new versions/sessions model, removing `list_agents`, `threads`,
  `messages`, and `runs`. The module now builds an `azure.ai.agents.AgentsClient`
  (installed: 1.2.0b6) directly against the same `PROJECT_ENDPOINT` — this client
  carries the classic surface the module was written for. Also
  `messages.list(order=...)` accepts `"desc"`/`"asc"`, not `"descending"`.
  (The stage-4 "first-run caveat" in GETTING_STARTED predicted exactly this
  failure mode and location.)
- **`.env` was documented but never loaded.** `python-dotenv` was in
  `requirements.txt` and every doc said "set it in `.env`", yet no code called
  `load_dotenv()` — live mode could not be enabled locally as documented (it
  worked in Azure only because App Service injects app settings as real
  environment variables). `scripts/run_demo.py` and `backend/main.py` now load
  the demo-root `.env` at startup.
- **`infra/variables.tf` — stale model defaults.** `gpt-4.1/2025-04-14` is in
  "deprecating" state and Azure refuses new deployments of it
  (`ServiceModelDeprecating`); the pinned reasoning version `gpt-5.4/2026-01-15`
  no longer exists in the catalog (the real gpt-5.4 version is `2026-03-05`).
  New defaults, verified deployable in eastus2: chat **gpt-5.1/2025-11-13**
  (deprecates 2027-05), reasoning **gpt-5.4/2026-03-05** (deprecates 2027-03).
  `terraform.tfvars.example` now says how to re-check
  (`az cognitiveservices model list -l <location> -o table`).
- **`infra/main.tf` — `project_management_enabled = true`** on the Foundry
  account (required before a Foundry project can be created under it; was
  patched manually via `az rest` during the walkthrough, now codified).

### Documented (new operational knowledge)

- **The Foundry project is still created outside Terraform** (the `main.tf` TODO
  stands). The working one-time `az rest` command — and the resulting
  `PROJECT_ENDPOINT` format — are documented in `main.tf`'s closing comment,
  `infra/README.md`, and GETTING_STARTED stage 4.
- **Local live runs need a data-plane role.** Subscription Owner does not include
  Agents API data actions. Grant the signed-in user **Azure AI Developer** on the
  Foundry account. (This tenant does not have the newer "Azure AI User" role.)
- **App Service quota can be 0.** The stage-5 web app failed with a 401 quota
  error ("Total VMs: current limit 0") — a managed-subscription policy, not a
  config bug. Foundry/model resources are unaffected. Options: quota request
  (aka.ms/antquotahelp) or a different subscription for the web app.
- **Windows-on-ARM:** the azurerm/archive providers ship no `windows_arm64`
  builds; use the `windows_amd64` Terraform binary side-by-side (runs under x64
  emulation). Matches the existing stage-0 note.
- **Git Bash path mangling:** `/subscriptions/...` scopes get rewritten to
  Windows paths, surfacing as `MissingSubscription`; prefix az commands with
  `MSYS_NO_PATHCONV=1`.

### Known issues (open)

- **Stage 5 blocked on App Service quota** in the test subscription (see above).
- **Console mojibake on Windows:** `run_demo.py` prints `�` where em-dashes
  appear when the console is cp1252. Cosmetic; a
  `sys.stdout.reconfigure(encoding="utf-8")` at startup would fix it.
- **`prompt_injection` "After" view** shows PRESS-201 as `down` even though the
  forged event was rejected and the schedule unchanged. If the guardrail is
  meant to quarantine the *entire* event, the machine-status change leaking
  through may be unintended — unreviewed.
- **Foundry project not Terraform-managed** (azapi resource pending; manual
  `az rest` step documented).
