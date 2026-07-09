# Signal-to-Service — Predictive maintenance + field service agent

> 🏭 **Manufacturing** · *from the signal to the action*
>
> A telemetry anomaly arrives → the agent **diagnoses** the failure mode and
> remaining useful life → **retrieves and cites** the correct SOP from the manuals
> (RAG) → a human **approves** → the agent **creates the work order**, **schedules**
> a technician and **attaches the SOP**.

This demo follows the AgentVerse demo conventions: a single-container FastAPI app
that serves a vanilla-JS UI at `/` and streams the agent reasoning over
Server-Sent Events, orchestrated with the **Microsoft Agent Framework (MAF)**.

---

## Architecture

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

### The three agents (persistent Foundry prompt agents, all `gpt-4.1`)

| Agent | Role |
|-------|------|
| `signal-to-service-diagnosis-agent` | Classifies the failure mode (`bearing` / `overheating` / `overcurrent` / `imbalance`), criticality and remaining useful life (RUL) from the telemetry window. |
| `signal-to-service-knowledge-agent` | Summarises and **cites** the correct SOP from the passages retrieved by the app's own RAG layer. |
| `signal-to-service-action-agent`    | Drafts the technician work-order summary. |

### RAG over the manuals — one contract, two backends

Retrieval runs in the app's own code (`app/backend/rag.py`) behind a single
function, `retrieve_sop(query, failure_mode)`, so the local and cloud paths cite
the **same** SOP:

* **Local TF-IDF** (default) — pure-Python cosine over the bundled SOP markdown in
  `app/data/sops/`. No Azure AI Search required to run locally.
* **Azure AI Search** — the same SOP chunks indexed in Search, used automatically
  when `AZURE_SEARCH_ENDPOINT` is set.

### Mocks (self-contained, local-first)

| Mock | Where |
|------|-------|
| Telemetry stream (healthy + degrading-to-anomaly) | `app/backend/telemetry.py` |
| Asset catalog (4 machines) | `app/data/assets.json` |
| SOP manuals corpus (4 SOPs) | `app/data/sops/*.md` |
| CMMS (work orders) + run state | `app/backend/cmms.py` (SQLite) |
| Field-service scheduler (3 technicians) | `app/backend/scheduler.py` |

The run state (diagnosis + approved proposal) is stored **server-side** keyed by a
`run_id`; the browser only holds the id, so the approved work order cannot be
tampered with client-side. Work-order creation is **idempotent** per run.

---

## Quick start

### Prerequisites
* Python 3.11
* `az login` with access to an Azure AI Foundry project that has a `gpt-4.1`
  deployment (the demo reuses the shared AgentVerse Foundry project by default).

### 1. Install
```powershell
cd src/signal-to-service
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Configure
```powershell
Copy-Item app/.env.example app/.env
# edit app/.env → set PROJECT_ENDPOINT to your Foundry project.
# Leave AZURE_SEARCH_ENDPOINT empty to use the local TF-IDF retriever.
```

### 3. Register the three prompt agents (idempotent)
```powershell
.\.venv\Scripts\python.exe -m app.backend.bootstrap_agents
```

### 4. Run
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.backend.main:app --host 0.0.0.0 --port 8767
```
Open <http://localhost:8767>, pick an asset and click **⚠ Inject anomaly**. Watch
the agents diagnose and cite the SOP, then **Approve & dispatch** to create the
work order.

---

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/assets` | Asset catalog. |
| GET | `/api/telemetry?asset=&series=healthy\|degrading` | A telemetry window. |
| GET | `/api/diagnose?asset=&series=degrading` | **SSE** — Phase A (diagnose + retrieve), ends `awaiting_approval`. |
| POST | `/api/approval` `{run_id, decision, reason}` | Records the governance decision. |
| GET | `/api/dispatch?run_id=` | **SSE** — Phase B (create work order + schedule). |
| GET | `/healthz` | Health + active RAG backend. |

---

## Deploy

* **Standalone:** `infra/` provisions the demo's own Azure AI Foundry account,
  `gpt-4.1`, and an Azure AI Search service + SOP index. See `infra/README.md`.
* **Unified (AgentVerse portal):** the demo joins the platform via `agentverse.yaml`
  and an entry in the root `infra/demos.auto.tfvars` — see
  [`docs/adding-a-demo.md`](../../docs/adding-a-demo.md). The unified deploy shares
  the platform's Foundry project + `gpt-4.1` and uses the **bundled local RAG** (no
  Azure AI Search is provisioned); to enable the Search backend, deploy the
  standalone `infra/` instead. As with the other demos, agent registration is a
  default-off hook: after the first unified `terraform apply`, run the bootstrap
  once (`terraform output registration_commands`, executed from the repo root) so
  `/api/diagnose` can resolve the three prompt agents.

## Observability

Set `APPLICATIONINSIGHTS_CONNECTION_STRING` (injected by the unified deploy) to
trace each phase. Every SSE event carries the `run_id` and a monotonic `seq` for
correlation.
