> **📐 Proposed standardized README.** This file follows the AgentVerse standard demo
> presentation structure ([template](../templates/demo-scaffold/README-TEMPLATE.md)).
> The author's original [README.md](README.md) remains the canonical documentation —
> all setup detail lives there; this file organizes the demo for presentation.

---

# Signal-to-Service

> From a telemetry anomaly to a scheduled, SOP-backed work order — with a human
> approving the action in the middle. *From the signal to the action.*

| | |
|---|---|
| **Industry / scenario** | Manufacturing · predictive maintenance + field service |
| **Audience** | Operations / maintenance and field-service teams; anyone evaluating grounded, governed agent actions |
| **Status** | Experimental |
| **Difficulty** | Intermediate |
| **Orchestration** | Event-triggered sequential workflow + human-in-the-loop approval gate |
| **Models** | gpt-4.1 (all three agents) |
| **Azure services** | Azure AI Foundry · Azure AI Search (optional — local TF-IDF is the default retriever) |
| **Stack** | MAF · FastAPI + SSE · vanilla HTML/JS · Terraform |
| **Runs locally without Azure?** | Partially — telemetry, CMMS, scheduler and RAG are all local mocks, but the three prompt agents need a Foundry project with `gpt-4.1` |
| **Author & original docs** | @heblasco · [README.md](README.md) |

---

## 1 · The story

A vibration sensor on a conveyor motor starts drifting. In most plants, what follows is
human glue: someone notices the alert (eventually), estimates the failure mode, searches
PDF manuals for the right procedure, opens a work order in the CMMS, and finds a
technician with the right skills who is actually available. Every hand-off loses time,
and the machine keeps degrading — the difference between a planned intervention and an
unplanned line stop is often exactly that lost afternoon.

This demo closes the whole chain. When a telemetry anomaly crosses the threshold, a
**diagnosis agent** classifies the failure mode, its criticality and the remaining
useful life. A **knowledge agent** then retrieves the *correct* standard operating
procedure from the manuals and — crucially — **cites it**. Then the pipeline stops:
a human reviews the diagnosis and the proposed action, and only after explicit
**approval** does the **action agent** draft the work order, create it in the CMMS,
schedule a suitable technician and attach the SOP.

Why agents? Diagnosis from a raw telemetry window and selecting the right procedure out
of a manual corpus are judgment-and-language problems. But the demo is equally clear
about the boundary of that judgment: the action that touches real systems sits behind a
human gate, the retrieval is grounded and cited rather than remembered, and the approved
proposal is held server-side so what was approved cannot be altered.

---

## 2 · The business case

The demo addresses the maintenance and field-service cost structure: the gap between
detecting a degrading asset and executing the right intervention is where downtime,
repeat visits and compliance risk accumulate.

| Business KPI | Without agents | Impact demonstrated |
|---|---|---|
| **Unplanned downtime** | Degradation is noticed late; failures arrive as line stops | Anomaly detection triggers the pipeline while the asset still has remaining useful life, converting unplanned failure into planned intervention |
| **Time from signal to scheduled intervention** | An afternoon or more of manual triage, manual lookup and CMMS entry | Under a minute from anomaly to an approved, scheduled, SOP-backed work order |
| **First-time fix rate** | Technician arrives without the right procedure or the wrong skills for the failure mode | The correct SOP is attached to the work order and the technician is matched by skill and availability |
| **Maintenance compliance / auditability** | Procedure selection undocumented; approvals informal | The SOP is cited from the governed corpus, and every action is preceded by a recorded human approval, correlated per `run_id` |
| **Maintenance planning effort** | Skilled staff spend time on triage and administrative glue | Human effort concentrates on a single decision: approve or reject a fully-prepared proposal |

The KPI that carries the argument is **signal-to-intervention time**, because it is what
converts predictive-maintenance sensing (which many plants already have) into avoided
downtime (which most still do not capture). The citation and approval mechanics are what
make the acceleration acceptable to quality and safety functions.

---

## 3 · The architecture

The ASCII diagram in [README.md](README.md#architecture) shows the full flow. In
summary — two phases separated by a human gate:

```
telemetry anomaly ──► Phase A (SSE /api/diagnose)
                        DiagnosisExecutor ──► KnowledgeExecutor (RAG + citation)
                              ▼
                  ⛨ human approval gate (POST /api/approval)
                              ▼ approve
                      Phase B (SSE /api/dispatch)
                        action-agent drafts ► scheduler assigns ► CMMS creates WO (+SOP)
```

### Components

| Component | Where | Role |
|---|---|---|
| Backend + SSE | [app/backend/main.py](app/backend/main.py) | FastAPI single-container app; serves the UI at `/` and streams both phases |
| RAG layer | [app/backend/rag.py](app/backend/rag.py) | One contract, `retrieve_sop(query, failure_mode)`, two backends: local TF-IDF (default) or Azure AI Search |
| Telemetry simulator | [app/backend/telemetry.py](app/backend/telemetry.py) | Healthy and degrading-to-anomaly series for 4 assets |
| CMMS mock | [app/backend/cmms.py](app/backend/cmms.py) | SQLite work orders + server-side run state, keyed by `run_id` |
| Scheduler mock | [app/backend/scheduler.py](app/backend/scheduler.py) | 3 technicians assigned by skill and availability |
| SOP corpus | [app/data/sops/](app/data/sops/) | 4 markdown manuals — the ground truth the knowledge agent must cite |
| Infra | [infra/](infra/) | Terraform: standalone Foundry + gpt-4.1 + Azure AI Search + SOP index |

### The agents

All three are persistent Foundry prompt agents on `gpt-4.1`, registered by
[app/backend/bootstrap_agents.py](app/backend/bootstrap_agents.py):

| Agent | Kind | Job |
|---|---|---|
| `signal-to-service-diagnosis-agent` | LLM agent | Classifies failure mode (`bearing`/`overheating`/`overcurrent`/`imbalance`), criticality and RUL from the telemetry window |
| `signal-to-service-knowledge-agent` | LLM agent + app RAG | Summarises and **cites** the correct SOP from the passages retrieved by the app's own RAG layer |
| `signal-to-service-action-agent` | LLM agent + app tools | Drafts the work-order summary; app code creates the WO and assigns the technician |

---

## 4 · Agentic patterns

| Pattern | Where in this demo | Why it matters here |
|---|---|---|
| **Event-triggered orchestration** | Anomaly threshold → pipeline start | The agent chain begins from a machine signal, not a human prompt — "beyond chat" made literal |
| **Sequential workflow** | Phase A executors in [app/backend/agents.py](app/backend/agents.py) | Diagnosis feeds retrieval; clean structured hand-off |
| **Human-in-the-loop approval gate** | `POST /api/approval` separating Phase A from Phase B | The agent *proposes*; only an explicit human decision releases the real-world action |
| **RAG with citations** | [app/backend/rag.py](app/backend/rag.py) + knowledge agent | The SOP is retrieved and cited, not recalled — and the single `retrieve_sop` contract guarantees local and cloud paths cite the *same* SOP |
| **Tool-mediated actions** | `create_work_order`, `assign_technician` | The LLM drafts; deterministic app code performs the side effects |
| **Tamper-resistant server-side state** | Run state keyed by `run_id` in [app/backend/cmms.py](app/backend/cmms.py) | The browser only holds an id — what was approved is what gets dispatched; WO creation is idempotent per run |
| **Correlated observability** | `run_id` + monotonic `seq` on every SSE event; App Insights | Each phase of every run is traceable end to end |

---

## 5 · Demonstration guide

**Duration:** ~8 min · **Requires Azure live:** yes (a Foundry project with `gpt-4.1`);
RAG, telemetry, CMMS and scheduler are all local, which keeps the operational surface
small.

### Preparation checklist

- [ ] `az login` completed; `app/.env` with `PROJECT_ENDPOINT` set (leave
      `AZURE_SEARCH_ENDPOINT` empty → local TF-IDF retriever, zero extra dependencies)
- [ ] Agents registered once: `python -m app.backend.bootstrap_agents`
- [ ] App running: `python -m uvicorn app.backend.main:app --port 8767` → http://localhost:8767
- [ ] One SOP from [app/data/sops/](app/data/sops/) open in an editor, ready to display as the source of the citation

### Demonstration sequence

1. Show the asset dashboard with healthy telemetry. Establish the premise: no one is
   conversing with anything — the trigger will be the machine itself.
2. Select an asset and click **⚠ Inject anomaly**. Follow the Phase A stream as the
   diagnosis agent names the failure mode, criticality and remaining useful life.
3. Pause on the knowledge agent's output: it **cites the SOP**. Display the actual
   markdown file from [app/data/sops/](app/data/sops/) alongside it — the citation is
   real and verifiable.
4. Point out that the pipeline has stopped at `awaiting_approval`: the agents have done
   everything except act. Click **Approve & dispatch**.
5. Phase B streams: work order drafted → technician selected by skill and availability →
   work order created in the CMMS with the SOP attached. Show the finished work order.

### Key moments

- The **citation**: the agent does not advise "consult the manual" — it quotes the
  correct SOP, and the source file can be opened to verify it.
- The **approval gate**: a single explicit decision separates diagnosis from action, and
  the approved proposal is held server-side where it cannot be altered.
- The end-to-end span: signal → diagnosis → cited procedure → scheduled technician, in
  under a minute.

---

## 6 · Additional resources

### API surface

Six small endpoints (assets, telemetry, diagnose-SSE, approval, dispatch-SSE, healthz) —
table in [README.md](README.md#api). `/healthz` also reports which RAG backend is active.

### Two deployment paths

- **Standalone:** [infra/](infra/) provisions the demo's own Foundry account, `gpt-4.1`
  and an Azure AI Search service + SOP index ([infra/README.md](infra/README.md);
  [scripts/seed_search_index.py](scripts/seed_search_index.py) seeds the index).
- **Unified (AgentVerse portal):** joins the platform via [agentverse.yaml](agentverse.yaml)
  and the root `infra/demos.auto.tfvars`, sharing the platform's Foundry project and using
  the bundled local RAG. After the first apply, run the registration hook once
  (`terraform output registration_commands`). See [docs/adding-a-demo.md](../../docs/adding-a-demo.md).

### Observability

Set `APPLICATIONINSIGHTS_CONNECTION_STRING` (injected by the unified deploy) to trace
each phase; every SSE event carries `run_id` and `seq` for correlation.
