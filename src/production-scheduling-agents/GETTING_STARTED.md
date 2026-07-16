# Getting started — from nothing to full deployment

A step-by-step path you can follow top to bottom. Each stage builds on the one
before, and each one tells you **what you should see** so you know it worked.

Every stage below was executed end-to-end on **2026-07-09** (first full live run);
statuses reflect what actually happened.

| Stage | What you get | Needs Azure? | Status |
|---|---|---|---|
| [0](#stage-0--prerequisites) | Tools installed | no | ready |
| [1](#stage-1--run-the-demo-with-zero-azure-5-minutes) | The whole demo running locally (replay mode) | **no** | ✅ verified |
| [2](#stage-2--understand-what-you-just-saw) | The mental model | no | ✅ verified |
| [3](#stage-3--provision-azure-with-terraform) | Foundry account + models in your subscription | yes | ✅ verified |
| [4](#stage-4--run-the-live-agents) | Real Foundry Agents making the decisions | yes | ✅ verified live |
| [5](#stage-5--full-cloud-deployment) | The demo hosted in Azure, URL-only | yes | ✅ verified (Container Apps) |
| [Bonus](#bonus--the-web-dashboard-locally) | The planner dashboard on localhost | no | ✅ verified |

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
an Azure AI Foundry account, the two model deployments (gpt-5.1 chat + gpt-5.4 reasoning),
and Application Insights.

```bash
az login                             # sign in; pick the right subscription
cd infra
cp terraform.tfvars.example terraform.tfvars   # edit: pick a foundry_account_name prefix (a random suffix is appended)
terraform init
terraform apply
```

**You should see:** `Apply complete!` after ~5 minutes, then:

```bash
terraform output                     # foundry_endpoint, model deployment names, ...
```

> **Model availability note (learned on the 2026-07-09 first apply):** model/version
> pairs age out. Azure refuses **new** deployments of models in "deprecating" state
> even though they still appear in listings — `gpt-4.1/2025-04-14` failed exactly
> this way (`ServiceModelDeprecating`). Before applying, check what your region
> offers and pin versions that exist:
>
> ```bash
> az cognitiveservices model list -l eastus2 -o table
> ```
>
> Current verified defaults: chat `gpt-5.1/2025-11-13`, reasoning `gpt-5.4/2026-03-05`.
> Your subscription also needs TPM quota for those models in your region
> (`az cognitiveservices usage list -l eastus2`); lower `model_capacity` if tight.

---

## Stage 4 — Run the live agents

Two one-time Azure steps first (Terraform doesn't cover them yet):

```bash
# 1. Create the Foundry *project* under the account (see the note in infra/main.tf
#    for the template). Example from the 2026-07-09 run:
az rest --method put \
  --url "https://management.azure.com/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<foundry-account>/projects/<project>?api-version=2025-06-01" \
  --body '{"location":"eastus2","identity":{"type":"SystemAssigned"},"properties":{}}'

# 2. Give YOUR user the Agents data-plane role (subscription Owner is NOT enough):
MSYS_NO_PATHCONV=1 az role assignment create --role "Azure AI Developer" \
  --assignee-object-id "$(az ad signed-in-user show --query id -o tsv)" \
  --assignee-principal-type User \
  --scope "<foundry account resource id>"
```

Then wire up the app:

```bash
cd ..                                # back to the demo root
pip install -r requirements.txt      # the full dependency set (Azure SDKs)
cp .env.example .env
# In .env set:
#   PROJECT_ENDPOINT=https://<foundry-account>.services.ai.azure.com/api/projects/<project>
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

> ✅ **First live run completed 2026-07-09** — and the caveat that used to sit here
> proved correct: the SDK surface *had* shifted, and both fixes were local to
> `agents/shared/foundry.py`. `azure-ai-projects` 2.x replaced its `.agents` API
> with a versions/sessions model, so the module now uses `azure.ai.agents.AgentsClient`
> directly (same project endpoint, same threads/messages/runs surface), and
> `messages.list(...)` takes `order="desc"`, not `"descending"`. All four disruptions
> then produced the correct decision class live (auto_reschedule 0.90 / escalate 0.60 /
> reject 1.00 / auto_reschedule 0.86), fixtures were re-recorded from those runs, and
> the eval gate stayed at 100%. Details in [CHANGELOG.md](CHANGELOG.md).

---

## Stage 5 — Full cloud deployment

The same `terraform apply` from stage 3 also hosts the demo. The `hosting`
variable picks the path:

- **`containerapp` (default, verified 2026-07-09)** — Azure Container Registry +
  **Azure Container Apps**. Terraform stages a clean source context (from the same
  `app.zip`), builds the image *in Azure* with `az acr build` (no local Docker
  needed — works on Windows-on-ARM laptops), and runs it with scale-to-zero and
  HTTPS ingress. Expandable later: sidecars, Dapr, more services in the same
  environment. One-time prerequisite per subscription:
  `az provider register --namespace Microsoft.App --wait`.
- **`appservice`** — Linux App Service via `zip_deploy_file`; Oryx installs
  `requirements.txt` server-side. Needs App Service VM quota (see the note below).
- **`none`** — skip hosting; stages 1–4 don't need it.

The entire lifecycle from a fresh laptop:

```bash
git clone <repo> && cd agentverse/src/production-scheduling-agents/infra
az login
az provider register --namespace Microsoft.App --wait   # once per subscription
cp terraform.tfvars.example terraform.tfvars   # pick unique foundry_account_name + webapp_name
terraform init && terraform apply
terraform output demo_url
```

**You should see:** `demo_url = "https://<your-app>...azurecontainerapps.io"`.
Open it — the Gantt board, the disruption buttons, the agent feed, the escalation
inbox. (First request cold-starts the scaled-to-zero replica: ~20 s, then fast.)

Deliberate defaults:

- **The hosted demo runs in replay mode** (`PROJECT_ENDPOINT` empty) — deterministic,
  zero model cost, immune to quota hiccups mid-presentation. To go live, set the
  `webapp_project_endpoint` variable and re-apply; the app's managed identity
  already has model access (`Cognitive Services User` on the Foundry account).
- **Code updates are also `terraform apply`** — the source hash drives both the
  zip deploy and the image tag, so infra and code never drift apart.
- **`webapp_location`** can host the app in a different region than the AI
  resources when the main region lacks hosting quota.

> ✅ **Verified 2026-07-09** on a managed subscription, after two real-world
> findings (full story in [CHANGELOG.md](CHANGELOG.md)):
>
> 1. **App Service quota was 0 "Total VMs"** in eastus2 (all tiers, including F1) —
>    a managed-subscription policy. That's why `containerapp` is the default: ACA
>    draws on a different quota bucket and deployed fine in the same region.
>    (westus2 *did* have App Service quota, so `hosting = "appservice"` +
>    `webapp_location = "westus2"` is a working fallback.)
> 2. **`az acr build` must not run from the demo root.** It ignores `.dockerignore`
>    when packing the upload, so it would ship `infra/` — including
>    `terraform.tfstate` — into the build context (and it collides with Terraform's
>    state lock mid-apply). The provisioner therefore stages the context from
>    `app.zip`, and queues the build with `--no-logs` because the az CLI's Windows
>    build crashes streaming UTF-8 build logs (the frontend's emoji) through its
>    cp1252 console layer.

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
| `ServiceModelDeprecating` on `terraform apply` | That model/version no longer accepts new deployments. Pick a current one: `az cognitiveservices model list -l <location> -o table`, update `terraform.tfvars`. |
| App Service plan fails: 401, "Total VMs ... limit 0" | Your subscription has zero App Service quota in that region (common on managed/sandbox subs). Use the default `hosting = "containerapp"` (different quota bucket), try `webapp_location = "<other-region>"`, or request an increase (aka.ms/antquotahelp). Stages 1–4 don't need hosting at all. |
| `MissingSubscriptionRegistration ... namespace 'Microsoft.App'` | One-time: `az provider register --namespace Microsoft.App --wait`, then re-apply. |
| `az acr build` fails with `UnicodeEncodeError: 'charmap' codec ...` | The az CLI's Windows build crashes streaming UTF-8 build logs. The Terraform provisioner already queues with `--no-logs` and polls; if running `az acr build` by hand, add `--no-logs`. |
| `az acr build` from the demo root: `Permission denied` / huge upload | It ignores `.dockerignore` when packing and tries to ship `infra/` (locked Terraform state, tfstate secrets). Build from a staged clean context — the provisioner does this from `app.zip`. |
| Live run: 403 / `PermissionDenied` from the Agents API | Grant your user **Azure AI Developer** on the Foundry account (Owner alone lacks data-plane actions). See stage 4. |
| `Role 'Azure AI User' doesn't exist` | Older tenants don't have that role yet — use **Azure AI Developer** instead. |
| `az` errors with `MissingSubscription` in Git Bash | Git Bash rewrote the `/subscriptions/...` scope into a Windows path. Prefix the command with `MSYS_NO_PATHCONV=1`. |
| Live run: `AttributeError ... 'list_agents'` or bad `order` value | Your `foundry.py` predates the 2026-07-09 SDK fix — it must use `azure.ai.agents.AgentsClient` and `order="desc"`. Pull latest. |
| `.env` seems ignored when running locally | Fixed 2026-07-09: `scripts/run_demo.py` and `backend/main.py` call `load_dotenv()`. If you see this, pull latest. |
