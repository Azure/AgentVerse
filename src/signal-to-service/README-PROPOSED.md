> **📐 Proposal.** A self-contained, standardized README following the AgentVerse
> [template](../templates/demo-scaffold/README-TEMPLATE.md), offered for the demo author
> to adopt — and adapt — as this demo's README.

---

# Signal-to-Service

> From a telemetry anomaly to a scheduled, procedure-backed work order — with a human
> approving the action in the middle. *From the signal to the action.*

**Contents:** [Part 1 · Business Brief](#part-1--business-brief) — present the demo ·
[Part 2 · Technical Brief](#part-2--technical-brief) — prepare and operate it

---

## Part 1 · Business Brief

### 1.1 At a glance

| | |
|---|---|
| **Scenario** | Manufacturing — predictive maintenance and field service |
| **Business outcome** | From a machine anomaly to an approved, procedure-backed, scheduled work order in under a minute |
| **Best suited for** | Operations, maintenance and field-service leaders; conversations about AI acting on real systems under human control |
| **Duration** | ~8 minutes |
| **Presenter effort** | Solo-capable after technical setup; the flow is short and scripted |
| **Demo reliability** | Good — the machine data, work-order system and technician roster are all built-in; only the three AI agents run in the cloud |
| **Contingency** | There is no offline mode — verify with a full test run shortly before presenting; if the cloud agents are unreachable, reschedule rather than improvise |

### 1.2 The story

A vibration sensor on a conveyor motor starts drifting. In most plants, what follows is
human glue: someone notices the alert (eventually), estimates what is failing, searches
PDF manuals for the right procedure, opens a work order in the maintenance system, and
finds a technician with the right skills who is actually available. Every hand-off loses
time, and the machine keeps degrading — the difference between a planned intervention
and an unplanned line stop is often exactly that lost afternoon.

This demo closes the whole chain. When a telemetry anomaly crosses the threshold, a
**diagnosis agent** classifies the failure mode, how critical it is, and how much useful
life the component has left. A **knowledge agent** then retrieves the *correct* standard
operating procedure from the maintenance manuals and — crucially — **cites it**, so the
answer can be checked against the source. Then the pipeline stops: a human reviews the
diagnosis and the proposed action, and only after explicit **approval** does the
**action agent** draft the work order, create it in the maintenance system, schedule a
suitable technician and attach the procedure.

Why agents? Diagnosing from a raw sensor window and selecting the right procedure out of
a manual corpus are judgment-and-language problems. But the demo is equally clear about
the boundary of that judgment: the action that touches real systems sits behind a human
gate, the retrieval is grounded and cited rather than remembered, and the approved
proposal is held on the server so what was approved cannot be altered afterwards.

### 1.3 The business case

| Business KPI | Without agents | Impact demonstrated |
|---|---|---|
| **Unplanned downtime** | Degradation is noticed late; failures arrive as line stops | Anomaly detection triggers the pipeline while the component still has useful life, converting unplanned failure into planned intervention |
| **Time from signal to scheduled intervention** | An afternoon or more of manual triage, manual lookup and system entry | Under a minute from anomaly to an approved, scheduled, procedure-backed work order |
| **First-time fix rate** | Technician arrives without the right procedure, or with the wrong skills for the failure | The correct procedure is attached to the work order and the technician is matched by skill and availability |
| **Maintenance compliance / auditability** | Procedure selection undocumented; approvals informal | The procedure is cited from the governed manual corpus, and every action is preceded by a recorded human approval |
| **Maintenance planning effort** | Skilled staff spend their time on triage and administrative glue | Human effort concentrates on a single decision: approve or reject a fully-prepared proposal |

The KPI that carries the argument is **signal-to-intervention time**, because it is what
converts predictive-maintenance sensing (which many plants already have) into avoided
downtime (which most still do not capture). The citation and approval mechanics are what
make the acceleration acceptable to quality and safety functions.

### 1.4 Delivering the demo

#### Presenter verification (5 minutes before)

- [ ] The demo page opens at the address provided by your technical contact and shows the asset dashboard with live telemetry
- [ ] A full test run (inject anomaly → approve → work order created) was completed shortly before the session — this is the only reliable check that the cloud agents are reachable
- [ ] You have the relevant maintenance procedure document open in a second window, ready to show as the source of the citation

#### Demonstration sequence

1. *(0–1 min)* Show the asset dashboard with healthy telemetry. *"Nobody is chatting
   with anything — the trigger for what follows will be the machine itself."*
2. *(1–3 min)* Select an asset and click **⚠ Inject anomaly**. Follow the stream as the
   diagnosis agent names the failure mode, its criticality, and the component's
   remaining useful life.
3. *(3–5 min)* Pause on the knowledge agent's output: it **cites the procedure**.
   Display the actual procedure document alongside it. *"The system does not say
   'consult the manual' — it quotes the correct procedure, and you can check the
   source."*
4. *(5–6 min)* Point out that the pipeline has stopped, awaiting approval: the agents
   have done everything except act. Click **Approve & dispatch**. *"One human decision
   separates diagnosis from action."*
5. *(6–8 min)* The dispatch completes: work order drafted → technician selected by
   skill and availability → work order created with the procedure attached. Close on
   the finished work order. *"Signal to scheduled service, in under a minute."*

#### Key moments

- The **citation**: the answer is grounded in the plant's own manuals and verifiable on
  the spot.
- The **approval gate**: a single explicit decision separates diagnosis from action —
  and what was approved is exactly what gets executed.
- The **end-to-end span**: signal → diagnosis → cited procedure → scheduled technician,
  in under a minute.

### 1.5 Anticipated questions

**"What if the diagnosis is wrong?"** — Nothing happens without a human. The pipeline
stops before any action, presents the diagnosis with its evidence and the cited
procedure, and a person approves or rejects. A rejected proposal ends there.

**"Is our data used to train the AI models?"** — No. Azure OpenAI Service does not use
customer data to train the underlying models; prompts and outputs stay within the
customer's tenant.

**"Would this integrate with our maintenance system?"** — The demo uses a built-in
work-order system and technician roster to stay self-contained; the pipeline is
designed so those two integration points (create work order, assign technician) map to
a real CMMS and workforce system in a deployment.

**"Where do the procedures come from?"** — From the customer's own manuals. The demo
ships with a small sample corpus; a deployment indexes the real procedure library, and
the citation mechanism is what keeps the AI accountable to it.

**"What does it cost to run?"** — Each run makes three short AI calls —
consumption-priced, a few cents. Production costs scale with alert volume and are
scoped in a pilot.

**"How long would a pilot take?"** — A pilot on one asset class with the customer's own
procedures and historical alerts is typically measured in weeks; the discovery workshop
(§1.6) is where the asset class and the procedure corpus are chosen.

### 1.6 From demo to next step

Propose an **asset-and-procedure discovery workshop**: pick one asset class with good
telemetry coverage, gather its procedure documents, and map who approves interventions
today. Output: a pilot scope where the pipeline runs against historical alerts and its
proposals are compared with what maintenance actually did.

### 1.7 What this demo is not

The telemetry is simulated, and the work-order system and technician roster are
built-in stand-ins, not a connected CMMS. The procedure corpus is four sample manuals.
The demo status is experimental: it demonstrates the pattern — grounded diagnosis,
cited procedures, human-gated action — not a finished maintenance product.

### Glossary

- **AI agent** — a model given a role, instructions and tools, able to decide how to
  complete a task rather than following a fixed script.
- **Telemetry** — the stream of sensor readings (vibration, temperature, current) from
  a machine.
- **Failure mode** — the specific way a component is failing (e.g. bearing wear,
  overheating).
- **RUL (remaining useful life)** — the estimated time a degrading component can still
  operate before failing.
- **SOP (standard operating procedure)** — the approved maintenance procedure document
  for a given failure.
- **CMMS** — the maintenance management system where work orders live.
- **Work order** — the formal instruction to perform a maintenance intervention.
- **RAG (retrieval-augmented generation)** — the AI retrieves passages from the actual
  manuals and answers from them, citing the source, instead of answering from memory.

> *To prepare the environment for this demo, share Part 2 with your technical contact.*

---

## Part 2 · Technical Brief

### 2.1 Technical profile

| | |
|---|---|
| **Status** | Experimental |
| **Orchestration** | Event-triggered sequential workflow + human-in-the-loop approval gate |
| **Models** | gpt-4.1 (all three agents) |
| **Azure services** | Azure AI Foundry · Azure AI Search (optional — local TF-IDF is the default retriever) |
| **Stack** | MAF · FastAPI + SSE · vanilla HTML/JS · Terraform |
| **Runs locally without Azure?** | Partially — telemetry, CMMS, scheduler and RAG are all local mocks, but the three prompt agents need a Foundry project with `gpt-4.1` |
| **Author** | @heblasco |

### 2.2 The architecture

Two phases separated by a human gate:

```
Telemetry stream (simulated) ──► anomaly crosses threshold ──► triggers the pipeline

  Phase A — MAF sequential workflow (streamed by GET /api/diagnose)
    ┌────────────────────┐        ┌────────────────────────┐
    │ DiagnosisExecutor  │ ─────► │ KnowledgeExecutor       │
    │  diagnosis-agent   │        │  our RAG + knowledge-   │
    │  failure mode,     │        │  agent (cites the SOP)  │
    │  criticality, RUL  │        └────────────────────────┘
    └────────────────────┘
                    │
                    ▼
        ⛨ Human-in-the-loop approval gate  (POST /api/approval)
                    │  approve
                    ▼
  Phase B — dispatch (streamed by GET /api/dispatch?run_id=)
    action-agent drafts the work order → scheduler assigns a technician →
    CMMS creates the work order (SOP attached).
```

#### Components

| Component | Where | Role |
|---|---|---|
| Backend + SSE | [app/backend/main.py](app/backend/main.py) | FastAPI single-container app; serves the UI at `/` and streams both phases |
| RAG layer | [app/backend/rag.py](app/backend/rag.py) | One contract, `retrieve_sop(query, failure_mode)`, two backends: local TF-IDF (default) or Azure AI Search |
| Telemetry simulator | [app/backend/telemetry.py](app/backend/telemetry.py) | Healthy and degrading-to-anomaly series for 4 assets |
| CMMS mock | [app/backend/cmms.py](app/backend/cmms.py) | SQLite work orders + server-side run state, keyed by `run_id` |
| Scheduler mock | [app/backend/scheduler.py](app/backend/scheduler.py) | 3 technicians assigned by skill and availability |
| SOP corpus | [app/data/sops/](app/data/sops/) | 4 markdown manuals — the ground truth the knowledge agent must cite |
| Infra | [infra/](infra/) | Terraform: standalone Foundry + gpt-4.1 + Azure AI Search + SOP index |

#### The agents

All three are persistent Foundry prompt agents on `gpt-4.1`, registered by
[app/backend/bootstrap_agents.py](app/backend/bootstrap_agents.py):

| Agent | Kind | Job |
|---|---|---|
| `signal-to-service-diagnosis-agent` | LLM agent | Classifies failure mode (`bearing`/`overheating`/`overcurrent`/`imbalance`), criticality and RUL from the telemetry window |
| `signal-to-service-knowledge-agent` | LLM agent + app RAG | Summarises and **cites** the correct SOP from the passages retrieved by the app's own RAG layer |
| `signal-to-service-action-agent` | LLM agent + app tools | Drafts the work-order summary; app code creates the WO and assigns the technician |

### 2.3 Agentic patterns

| Pattern | Where in this demo | Why it matters here | In business terms |
|---|---|---|---|
| **Event-triggered orchestration** | Anomaly threshold → pipeline start | The agent chain begins from a machine signal, not a human prompt | The machine raises its hand; nobody has to ask |
| **Sequential workflow** | Phase A executors in [app/backend/agents.py](app/backend/agents.py) | Diagnosis feeds retrieval; clean structured hand-off | Each specialist finishes the previous one's work |
| **Human-in-the-loop approval gate** | `POST /api/approval` separating Phase A from Phase B | The agent *proposes*; only an explicit human decision releases the real-world action | The agent prepares everything; your employee signs |
| **RAG with citations** | [app/backend/rag.py](app/backend/rag.py) + knowledge agent | The SOP is retrieved and cited, not recalled; the single `retrieve_sop` contract guarantees local and cloud paths cite the *same* SOP | The AI quotes your manual and shows the page |
| **Tool-mediated actions** | `create_work_order`, `assign_technician` | The LLM drafts; deterministic app code performs the side effects | The AI writes the form; the system files it |
| **Tamper-resistant server-side state** | Run state keyed by `run_id` in [app/backend/cmms.py](app/backend/cmms.py) | The browser only holds an id — what was approved is what gets dispatched; WO creation is idempotent per run | What was signed is what gets executed |
| **Correlated observability** | `run_id` + monotonic `seq` on every SSE event; App Insights | Each phase of every run is traceable end to end | Every run leaves a complete trace |

### 2.4 Technical setup

Run before a session; the end state is what §1.4's presenter verification checks.

- [ ] `az login` with access to a Foundry project that has a `gpt-4.1` deployment (the demo reuses the shared AgentVerse Foundry project by default)
- [ ] venv + `pip install -r requirements.txt`; `app/.env` from `app/.env.example` with `PROJECT_ENDPOINT` set (leave `AZURE_SEARCH_ENDPOINT` empty → local TF-IDF retriever)
- [ ] Register the agents once (idempotent): `python -m app.backend.bootstrap_agents`
- [ ] Run: `python -m uvicorn app.backend.main:app --port 8767` → http://localhost:8767
- [ ] Execute one full test run (inject anomaly → approve → work order) shortly before the session — there is no offline fallback for the agents
- [ ] `/healthz` reports health and the active RAG backend

### 2.5 Additional resources

#### API surface

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/assets` | Asset catalog |
| GET | `/api/telemetry?asset=&series=healthy\|degrading` | A telemetry window |
| GET | `/api/diagnose?asset=&series=degrading` | **SSE** — Phase A (diagnose + retrieve), ends `awaiting_approval` |
| POST | `/api/approval` `{run_id, decision, reason}` | Records the governance decision |
| GET | `/api/dispatch?run_id=` | **SSE** — Phase B (create work order + schedule) |
| GET | `/healthz` | Health + active RAG backend |

#### Two deployment paths

- **Standalone:** [infra/](infra/) provisions the demo's own Foundry account, `gpt-4.1`
  and an Azure AI Search service + SOP index ([infra/README.md](infra/README.md);
  [scripts/seed_search_index.py](scripts/seed_search_index.py) seeds the index).
- **Unified (AgentVerse portal):** joins the platform via [agentverse.yaml](agentverse.yaml)
  and the root `infra/demos.auto.tfvars`, sharing the platform's Foundry project and using
  the bundled local RAG. After the first apply, run the registration hook once
  (`terraform output registration_commands`). See [docs/adding-a-demo.md](../../docs/adding-a-demo.md).

#### Observability

Set `APPLICATIONINSIGHTS_CONNECTION_STRING` (injected by the unified deploy) to trace
each phase; every SSE event carries `run_id` and `seq` for correlation.
