> **📐 Proposed standardized README.** This file follows the AgentVerse standard demo
> presentation structure ([template](../templates/demo-scaffold/README-TEMPLATE.md)).
> The author's original [README.md](README.md) remains the canonical documentation —
> all setup detail lives there; this file organizes the demo for presentation.

---

# Production Scheduling AI Agents

> Constraint-aware, self-healing production scheduling: an agentic control loop on top
> of existing ERP/MES systems that works like an experienced planner who never sleeps.

| | |
|---|---|
| **Industry / scenario** | Manufacturing · production planning & scheduling |
| **Audience** | Manufacturing / operations leaders evaluating agentic AI beyond chat |
| **Status** | Experimental (fully implemented; live Foundry path pending its first real-subscription run) |
| **Difficulty** | Intermediate |
| **Orchestration** | Orchestrator–workers + human-in-the-loop escalation ([PATTERNS.md](../templates/agentic-framework/PATTERNS.md) §5, §8) |
| **Models** | gpt-5.4 (simulator) · gpt-5.1 (orchestrator) |
| **Azure services** | Azure AI Foundry · Application Insights · App Service (Terraform) |
| **Stack** | MAF · FastAPI + SSE · vanilla HTML/JS (Gantt dashboard) · Terraform |
| **Runs locally without Azure?** | **Yes — by default.** Replay mode uses recorded agent fixtures; zero Azure dependencies, all 4 golden evals pass |
| **Author & original docs** | [README.md](README.md) · [GETTING_STARTED.md](GETTING_STARTED.md) |

---

## 1 · The story

A production schedule is only correct at the moment it is generated. Plants optimize it
overnight, and by mid-morning reality has drifted: a machine goes down, a material
shipment slips, a priority order lands mid-shift. Re-planning is slow and manual — a
planner must notice the disruption, work out which orders it touches, mentally simulate
alternatives, and push changes back into ERP/MES. That cycle takes hours, and every hour
shows up as idle lines, expedite fees and late deliveries. Skilled planners end up as
firefighters.

The root cause is architectural, not effort: batch optimizers answer *"what is the best
plan given a frozen snapshot?"*, while a factory needs *"what should we do **now**, given
what just changed?"* — continuously.

This demo treats scheduling as a continuous **Sense → Simulate → Decide → Act** loop run
by agents layered on top of the systems the plant already owns. A constraint monitor
classifies disruptions against hard vs. soft constraints; a simulator agent proposes and
scores alternative schedules; an orchestrator agent applies the best option autonomously
when the answer is clear — and escalates to the human planner *only* when the trade-off
is genuinely ambiguous, always with scored options and a plain-language rationale. A
dispatcher publishes the validated schedule back and notifies the work centers.

Why agents? Because the middle of that loop — weighing changeover cost against urgency,
labor balance, energy windows, a tier-1 SLA against three standard orders — is judgment.
And the demo's sharpest design decision is where agents are **not**: sensing and acting
stay deterministic code, and hard constraints are validated by a deterministic solver,
so no schedule violating safety or capacity can ever be published, regardless of what an
LLM proposes.

---

## 2 · The business case

This demo has an unusual advantage: its business KPIs are not claimed on a slide — they
are computed live on the dashboard's KPI strip ([backend/kpis.py](backend/kpis.py)) and
move as disruptions are resolved.

| Business KPI | Without agents | Impact demonstrated |
|---|---|---|
| **Time-to-adjust per disruption** | Hours: detection → analysis → decision → ERP/MES update, all manual | Minutes: the full loop closes automatically; measured live on the KPI strip |
| **Line idle time** | Accumulates while the broken schedule stays in force | Reduced directly by faster reflows; visible on the KPI strip after each disruption |
| **Schedule adherence** | Degrades through the shift as reality drifts from the overnight plan | Maintained by continuous adjustment; tracked live |
| **Planner interventions per shift** | Every disruption demands planner attention — planners as firefighters | Only genuinely ambiguous trade-offs escalate; the count is measured on the KPI strip |
| **On-time delivery to priority customers** | Tier-1 SLAs compete unmanaged with routine orders during firefighting | Tier-1 SLA protection is an explicit policy-gate rule and a scored dimension in every scenario |
| **Expedite and changeover costs** | Incurred reactively once the schedule has already collapsed | Changeover cost and downstream congestion are scored trade-offs in every proposed scenario |

The economic argument rests on **time-to-adjust**: every other KPI on the strip — idle
time, adherence, expedite fees — is a downstream function of how long a broken schedule
stays in force. The secondary argument is workforce leverage: planners recover the
capacity, demand and improvement work they were hired for.

---

## 3 · The architecture

Two Mermaid diagrams in [README.md](README.md#architecture) show the full control loop
and one disruption end-to-end. In summary:

```
ERP / MES / maintenance feeds
        ▼
1 SENSE    constraint-monitor (⚙️ code) — classify + prompt-injection guardrail
        ▼
2 SIMULATE scenario-simulator (🤖 gpt-5.4) → feasibility checker (⚙️ code) discards infeasible
        ▼
3 DECIDE   schedule-orchestrator (🤖 gpt-5.1) → policy gate (⚙️ code)
        ├─ clear best option ──────────────► 4 ACT
        └─ ambiguous ► 👤 planner chooses ─► 4 ACT
        ▼
4 ACT      schedule-dispatcher (⚙️ code) — re-validate → publish v+1 → notify
```

### Components

| Component | Where | Role |
|---|---|---|
| Pipeline | [backend/pipeline.py](backend/pipeline.py) | Wires the four stages into one run per disruption |
| Plant model + feasibility checker | [backend/plant.py](backend/plant.py) | Deterministic validation of every proposed move; applies chosen scenarios |
| Disruption classifier + guardrail | [backend/disruptions.py](backend/disruptions.py) | Hard/soft constraint classification; injection screen on free text from MES/ERP |
| LLM agents | [agents/scenario-simulator/](agents/scenario-simulator/), [agents/schedule-orchestrator/](agents/schedule-orchestrator/) | Each a folder of `agent.yaml` · `instructions.md` · `schemas.py` · `agent.py` |
| Replay fixtures | [agents/fixtures/](agents/fixtures/) | Recorded agent responses — the zero-Azure demo mode |
| Dashboard | [frontend/](frontend/) served by [backend/main.py](backend/main.py) | Gantt board, live agent feed, escalation inbox, KPI strip |
| CLI runner | [scripts/run_demo.py](scripts/run_demo.py) | Same pipeline without a browser; `--record` refreshes fixtures |
| Evals | [evals/](evals/) | Golden disruption scenarios gate every change |
| Infra | [infra/](infra/) | Terraform provisions Foundry + models + App Insights + App Service *and* ships the app code in one apply |

### The agents

| Agent | Kind | Model | Job |
|---|---|---|---|
| `constraint-monitor` | ⚙️ deterministic code | — | Classify feed events against hard/soft constraints; injection guardrail |
| `scenario-simulator` | 🤖 LLM agent | gpt-5.4 | Generate & score 2–3 alternative schedules; every proposal re-validated deterministically |
| `schedule-orchestrator` | 🤖 LLM agent | gpt-5.1 | Auto-apply vs. escalate vs. reject; a code policy gate enforces the rules |
| `schedule-dispatcher` | ⚙️ deterministic code | — | Re-validate (last line of defense), publish, notify work centers |

---

## 4 · Agentic patterns

| Pattern | Where in this demo | Why it matters here |
|---|---|---|
| **Orchestrator–workers** | [backend/pipeline.py](backend/pipeline.py) chaining simulator → orchestrator | Judgment split across specialized agents with structured hand-offs |
| **Human-in-the-loop escalation** | Policy gate → planner dashboard / `--choose` | Autonomy when clear, humans only for genuinely ambiguous trade-offs — with scored options, never raw alarms |
| **Deterministic guardrails around LLMs** | [backend/plant.py](backend/plant.py) `validate_moves()` + policy gate | The demo's thesis: LLMs reason and explain; hard constraints are enforced by code, so an infeasible schedule can never ship |
| **Prompt-injection defense** | [backend/disruptions.py](backend/disruptions.py) | Malicious free text from ERP/MES is rejected *before any LLM sees it* |
| **Eval gate** | [evals/run_evals.py](evals/run_evals.py) + [.github/workflows](.github/workflows/) | Golden disruption cases (incl. the injection case) gate every PR |
| **Replay / record fixtures** | [agents/fixtures/](agents/fixtures/), `--record` | Deterministic, zero-Azure, zero-latency demonstrations — reliability as a first-class feature |
| **Observability as product** | KPI strip ([backend/kpis.py](backend/kpis.py)) + tracing/token metrics | Idle time, adherence, interventions/shift, time-to-adjust — the business impact is measured live, not asserted |

---

## 5 · Demonstration guide

**Duration:** 10–12 min · **Requires Azure live:** **no** — replay mode is the default
and the recommended presentation mode; live Foundry agents are an optional extension.

### Preparation checklist

- [ ] `pip install pydantic pyyaml fastapi "uvicorn[standard]"` in a venv (replay mode needs nothing else)
- [ ] Dashboard running: `python -m uvicorn backend.main:app --port 8000` → http://localhost:8000
- [ ] Optionally a terminal prepared for the CLI steps (`scripts/run_demo.py`)
- [ ] If a browser is unavailable, the CLI runner demonstrates the identical pipeline: `python scripts/run_demo.py --disruption machine_down`

### Demonstration sequence

1. Open the dashboard: today's schedule as a Gantt board, all orders on plan. Establish
   the premise — this plan was optimized overnight and is about to meet reality.
2. Inject **machine down**. Walk through the agent feed: the monitor classifies it as a
   hard-constraint disruption, the simulator proposes 2–3 scored scenarios, the
   feasibility checker discards the infeasible ones, and the orchestrator applies the
   best option **autonomously**. The Gantt board reflows and the KPI strip updates.
3. Inject **material delay** — a genuinely ambiguous case. It arrives in the
   **escalation inbox** with scored options and a plain-language rationale; choose a
   scenario as the planner and the dispatcher publishes it. The point to establish: the
   agent absorbed the routine case and escalated the judgment call, with evidence.
4. Inject **prompt injection**: a poisoned free-text field from the ERP feed. The
   guardrail rejects it — the schedule is unchanged and **no LLM was ever invoked**.
5. Conclude with `python -m evals.run_evals` in the terminal: the golden scenarios that
   gate every change to these agents, all passing.

### Key moments

- The **Gantt reflow** seconds after a disruption — the hours of manual re-planning,
  eliminated and measured on screen (time-to-adjust).
- The **escalation inbox**: autonomy with accountability — scored options and a
  rationale, not a raw alarm.
- The **injection rejection**: security enforced before the model, not after it.

---

## 6 · Additional resources

### Zero-to-deployment walkthrough

[GETTING_STARTED.md](GETTING_STARTED.md) goes from nothing to a full cloud deployment
step by step — the README's Quick Start is the condensed version.

### One-apply cloud deploy

`cd infra && terraform apply` provisions Foundry, model deployments, App Insights and
App Service **and ships the app code** (zip deploy) in a single apply;
`terraform output demo_url` opens it. Windows ARM64 note: install the `windows_amd64`
Terraform build (azurerm ships no ARM64 Windows binaries).

### Live mode

With `PROJECT_ENDPOINT` set (from `terraform output`), the same runs drive real Foundry
agents; `--all --record` refreshes the replay fixtures afterwards. In replay mode, keep
to the four scripted disruptions — they are the ones with recorded fixtures.

### Also in the repository

- Full demo-repo governance: [.github/](.github/) CODEOWNERS, PR template, eval workflow,
  plus [CHANGELOG.md](CHANGELOG.md), [CONTRIBUTING.md](CONTRIBUTING.md), [LICENSE](LICENSE) (MIT).
- Per-folder READMEs in [agents/](agents/README.md), [backend/](backend/README.md),
  [frontend/](frontend/README.md), [evals/](evals/README.md), [infra/](infra/README.md),
  [scripts/](scripts/README.md).
- Catalog manifest: [agentverse.yaml](agentverse.yaml).
