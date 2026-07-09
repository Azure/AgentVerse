# Getting started — from nothing to full deployment

A step-by-step path you can follow top to bottom. Each stage builds on the one
before, and each one tells you **what you should see** so you know it worked.

Stages 0–3 work **today**. Stages 4–5 are marked with their current status.

| Stage | What you get | Needs Azure? | Status |
|---|---|---|---|
| [0](#stage-0--prerequisites) | Tools installed | no | ready |
| [1](#stage-1--run-the-demo-with-zero-azure-5-minutes) | The whole demo running locally (replay mode) | **no** | ✅ works today |
| [2](#stage-2--understand-what-you-just-saw) | The mental model | no | ✅ works today |
| [3](#stage-3--provision-azure-with-terraform) | Foundry account + models in your subscription | yes | ✅ works today |
| [4](#stage-4--run-the-live-agents) | Real Foundry Agents making the decisions | yes | ✅ works today (first-run caveat) |
| [5](#stage-5--full-cloud-deployment) | The demo hosted in Azure, URL-only | yes | ✅ built (first-apply caveat) |
| [Bonus](#bonus--the-web-dashboard-locally) | The planner dashboard on localhost | no | ✅ works today |

---

## Stage 0 — Prerequisites

Install once:

| Tool | Version | Check |
|---|---|---|
| Python | 3.12+ | `python --version` |
| Git | any recent | `git --version` |
| Azure CLI *(stages 3+)* | 2.60+ | `az --version` |
| Terraform *(stages 3+)* | 1.6+ | `terraform version` |

> **Windows-on-ARM laptop?** Install the **`windows_amd64`** Terraform zip from
> [releases.hashicorp.com](https://releases.hashicorp.com/terraform/), not the arm64
> one — the Azure provider ships no ARM64 Windows build, and the amd64 binary runs
> fine under Windows' x64 emulation.

You do **not** need Node, Docker, or any Azure access until stage 3.

---

## Stage 1 — Run the demo with zero Azure (5 minutes)

Everything in this stage runs from recorded agent responses ("replay mode"), so
no endpoint, no keys, no cost.

```bash
# 1. Get the code (skip if you already have the repo)
git clone <this-repo-url>
cd agentverse/src/production-scheduling-agents

# 2. A virtual environment with the two packages replay mode needs
python -m venv .venv
. .venv/bin/activate                 # PowerShell: .venv\Scripts\Activate.ps1
pip install pydantic pyyaml

# 3. The autonomy storyline: a machine goes down, the agents fix the schedule
python scripts/run_demo.py --disruption machine_down
```

**You should see:** the "Before" schedule, the agents thinking
(`constraint-monitor` → `scenario-simulator` → `schedule-orchestrator` →
`schedule-dispatcher`), and an "After" schedule where `ORD-7712` has moved from
the broken `CNC-102` to `CNC-104`. Outcome line: `auto_reschedule | schedule changed`.

Now the other two storylines:

```bash
# Human-in-the-loop: an ambiguous trade-off is escalated to YOU
python scripts/run_demo.py --disruption material_delay
#   -> shows three options and stops. Answer as the planner:
python scripts/run_demo.py --disruption material_delay --choose SCN-A

# Guardrail: a prompt injection hidden in an operator comment is rejected
python scripts/run_demo.py --disruption prompt_injection
#   -> Outcome: reject [security flag] | schedule unchanged
```

Finally, prove the whole thing with the eval gate:

```bash
python -m evals.run_evals
```

**You should see:** `[PASS]` on all four golden cases, `Pass rate: 100%`.

---

## Stage 2 — Understand what you just saw

Five sentences:

1. The demo is a **control loop**: *Sense → Simulate → Decide → Act*, run once per
   disruption ([backend/pipeline.py](backend/pipeline.py)).
2. **Two LLM agents** sit where judgment lives: [`scenario-simulator`](agents/scenario-simulator/)
   proposes and scores alternative schedules; [`schedule-orchestrator`](agents/schedule-orchestrator/)
   decides — apply autonomously, escalate to you, or reject.
3. **Deterministic code** guards them: the feasibility checker
   ([backend/plant.py](backend/plant.py)) discards any proposal violating hard
   constraints, and a policy gate corrects the orchestrator if it oversteps
   (low confidence, tier-1 SLA at stake, hallucinated scenario).
4. **Replay vs. live** is decided by one env var: no `PROJECT_ENDPOINT` → recorded
   fixtures ([agents/fixtures/](agents/fixtures/)); endpoint set → real Foundry Agents.
   Callers can't tell the difference.
5. The **golden dataset** ([evals/golden_dataset.json](evals/golden_dataset.json)) pins all
   of this down: any regression in prompts, fixtures, checker, or gate fails the gate.

Deeper reading: [README.md](README.md) (the why), [agents/README.md](agents/README.md)
(the roles), the agent cards in each `agents/<name>/README.md`.

---

## Stage 3 — Provision Azure with Terraform

One `terraform apply` creates everything the live agents need: a resource group,
an Azure AI Foundry account, the two model deployments (gpt-4.1 chat + reasoning),
and Application Insights.

```bash
az login                             # sign in; pick the right subscription
cd infra
cp terraform.tfvars.example terraform.tfvars   # edit: pick a globally-unique foundry_account_name
terraform init
terraform apply
```

**You should see:** `Apply complete!` after ~5 minutes, then:

```bash
terraform output                     # foundry_endpoint, model deployment names, ...
```

> Quota note: your subscription needs quota for the models in the region you chose
> (`eastus2` default). If the reasoning model has no quota, set
> `reasoning_model_name = "gpt-4.1"` in `terraform.tfvars` — the simulator works on
> gpt-4.1 too, just with plainer trade-off analysis.

---

## Stage 4 — Run the live agents

```bash
cd ..                                # back to the demo root
pip install -r requirements.txt      # the full dependency set (Azure SDKs)
cp .env.example .env
# In .env set:
#   PROJECT_ENDPOINT=<foundry_endpoint from terraform output>/api/projects/<your-project>
#   MODEL_DEPLOYMENT_NAME / REASONING_MODEL_DEPLOYMENT_NAME if you changed them

python scripts/run_demo.py --disruption machine_down    # now drives real Foundry Agents
```

**You should see:** the same storyline as stage 1, but slower (real model calls) —
and the agents + their decision threads visible in the
[Azure AI Foundry portal](https://ai.azure.com) under your project.

Then refresh the replay fixtures from real runs, so your offline demo replays
genuine model output:

```bash
python scripts/run_demo.py --all --record
python -m evals.run_evals            # still green with the re-recorded fixtures
```

> ⚠️ First-run caveat: the live Foundry path (`agents/shared/foundry.py`) was written
> against the current `azure-ai-projects` SDK but hasn't been exercised yet — if the
> SDK surface shifted, the fix will be local to that one file.

---

## Stage 5 — Full cloud deployment

The same `terraform apply` from stage 3 also creates a **Linux App Service and
ships the application code** via `zip_deploy_file`: Terraform zips the demo,
deploys it, Oryx installs `requirements.txt` server-side, and the app settings
(model names, App Insights) are wired automatically. The entire lifecycle from
a fresh laptop:

```bash
git clone <repo> && cd agentverse/src/production-scheduling-agents/infra
az login
cp terraform.tfvars.example terraform.tfvars   # pick unique foundry_account_name + webapp_name
terraform init && terraform apply
terraform output demo_url
```

**You should see:** `demo_url = "https://<your-webapp>.azurewebsites.net"`. Open it —
the Gantt board, the disruption buttons, the agent feed, the escalation inbox.
(First load can take ~1–2 min while Oryx finishes the pip install.)

Two deliberate defaults:

- **The hosted demo runs in replay mode** (`PROJECT_ENDPOINT` empty) — deterministic,
  zero model cost, immune to quota hiccups mid-presentation. To go live, set the
  `webapp_project_endpoint` variable and re-apply; the web app's managed identity
  already has model access (`Cognitive Services User` on the Foundry account).
- **Code updates are also `terraform apply`** — the zip's hash changes when files
  change, so infra and code never drift apart.

> ⚠️ First-apply caveat: this configuration passes `terraform validate`, but a full
> `apply` hasn't been executed against a real subscription yet — expect at most
> small tweaks (e.g. SKU/region quirks) on the first run.

---

## Bonus — the web dashboard locally

The same UI the cloud serves, on your machine (replay mode, no Azure):

```bash
pip install fastapi "uvicorn[standard]"
python -m uvicorn backend.main:app --port 8000
# open http://localhost:8000
```

**You should see:** the schedule board all green. Click **🔧 Machine down** — the
agents stream in the activity panel and the Gantt reflows. Click **📦 Material
delay** — an amber "Your call, planner" card appears with three options; pick one
and watch it publish. Click **🕵️ Injected comment** — a red rejection card, board
untouched.

---

## Where things can go wrong

| Symptom | Fix |
|---|---|
| `Replay mode: no fixture for agent ...` | Stick to the 4 scripted disruptions, or record fixtures live (`--all --record`). |
| `Incompatible provider version ... windows_arm64` | Install the amd64 Terraform build (see stage 0). |
| `DefaultAzureCredential` failures | `az login` again; check you're on the right subscription (`az account show`). |
| Model deployment quota errors on `terraform apply` | Lower `model_capacity` in `terraform.tfvars`, or switch region/model. |
| Live run fails inside `foundry.py` | See the stage-4 caveat — verify the `azure-ai-projects` SDK calls. |
