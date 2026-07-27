# Azure SRE Agent — AgentVerse demo

> A guided, zero-risk walkthrough of the Azure SRE Agent turning an incident signal into
> a root cause and a human-approved fix.

**Contents:** [Part 1 · Business Brief](#part-1--business-brief) — present the demo ·
[Part 2 · Technical Brief](#part-2--technical-brief) — prepare and operate it

---

## Part 1 · Business Brief

### 1.1 At a glance

| | |
|---|---|
| **Scenario** | Cloud operations / site reliability — investigating and remediating Azure incidents |
| **Business outcome** | A believable, end-to-end walkthrough of an AI agent turning a monitoring alert into a root cause and a proposed, human-approved fix |
| **Best suited for** | SRE, platform ops and reliability engineering leaders; conversations about AI acting near production under human control |
| **Duration** | ~8–10 minutes (walk one or two of the six seeded incidents) |
| **Presenter effort** | Fully solo-capable — no Azure credentials or setup needed; everything is pre-scripted |
| **Demo reliability** | Excellent — deterministic, seeded transcripts with no live Azure calls; identical every run |
| **Contingency** | None needed — nothing external can fail; if screen sharing drops, the sequence can be described verbally from the scenario table below |

### 1.2 The story

When something breaks in production, what usually follows is a scramble: someone
notices the alert, jumps between three or four different portals to find the right
logs, forms a hypothesis from memory and tribal knowledge, and — if they're careful —
gets a second opinion before touching anything. Every one of those steps takes time,
and quality depends entirely on who happened to be on call.

This demo shows the [Azure SRE Agent](https://learn.microsoft.com/azure/sre-agent/overview)
doing that work as a structured, auditable investigation: **signal → observe (via
telemetry connectors) → hypothesis → root cause → proposed remediation**, gated on
human approval. It ships with **six** seeded, hand-authored incidents shaped like real
production failures — a Container Apps memory-limit regression, an AKS secret-rotation
crash loop, Azure SQL DTU saturation, a Cosmos DB hot-partition throttle, an expired TLS
certificate, and DNS drift breaking Key Vault access — each stepped through as a
timeline that mirrors exactly how the real agent works, and each mapped to a
Well-Architected Framework pillar.

Why an agent, rather than a runbook or a dashboard? Because the interesting part isn't
retrieving one metric — it's chaining evidence across several telemetry sources into a
single, plain-English root cause, the same judgment call a senior on-call engineer makes
under pressure. And the demo is equally deliberate about the boundary of that judgment:
the agent investigates and proposes, but the action that would touch a real resource
sits behind an explicit human approval, shown here read-only and never executed.

### 1.3 The business case

| Business KPI | Without agents | Impact demonstrated |
|---|---|---|
| **Mean time to root cause** | Manual triage across multiple portals and logs, gated on who's on call and what they remember | The full signal-to-root-cause chain plays out as one continuous, evidence-backed timeline |
| **Consistency of incident investigation** | Quality varies by engineer; findings often live only in someone's memory or a chat thread | Every investigation follows the same structure and produces an auditable record — signal, evidence, hypothesis, root cause |
| **Governance / blast radius of AI in operations** | A justified worry that an autonomous agent could take unwanted action on production | Every proposed remediation is gated on an explicit human approval (Review mode); this demo shows that gate and never executes anything |
| **Reliability posture reporting** | Fixes and their rationale are rarely tied back to a framework | Each incident and its fix is explicitly mapped to a Well-Architected Framework pillar |

The KPI that opens the conversation is **mean time to root cause**, because that's the
number ops leaders already track. The row that closes it for a skeptical stakeholder is
**governance** — the approval gate is not a UI decoration, it's the reason this is safe
to show at all.

### 1.4 Delivering the demo

#### Presenter verification (5 minutes before)

- [ ] The demo page opens at the address provided and shows a **"Guided replay"** banner
  confirming no live Azure calls are made
- [ ] The scenario list shows **six** seeded incidents
- [ ] Selecting a scenario renders the full timeline: signal → telemetry queries → root
  cause → approval card → resolution
- [ ] The right-hand capabilities panel renders with working links to Microsoft Learn

#### Demonstration sequence

1. *(0–1 min)* Point at the **Guided replay** banner. *"Everything you're about to see
   is deterministic and pre-scripted — nothing here touches a live system, so it's zero
   cost and zero risk to run."*
2. *(1–3 min)* Open the **Container App 5xx spike** scenario. Walk the timeline: an
   Azure Monitor alert fires, the agent baselines the spike against a recent rollout,
   queries Log Analytics, diffs the revision via ARM, and lands on the root cause — a
   halved memory limit causing an OOM crash loop.
3. *(3–4 min)* Pause on the **approval card**. *"The agent proposes rolling back to the
   last healthy revision — it does not do it. That decision belongs to your engineer."*
   Point out the stated risk level next to the action.
4. *(4–5 min)* Show the **resolution** step to close the loop, then point at the
   Well-Architected pillar tags on the scenario. *"This isn't just 'AI fixed it' — it's
   tied back to the framework your team already reports against."*
5. *(5–7 min, technical rooms)* Open the right-hand panel: connectors, agent modes,
   approvals, RBAC, and the control/data-plane API, each linked to the official docs.
   *"This mirrors the real agent's actual capabilities, not a simplified mockup."*
6. *(Optional)* Run a second, differently-shaped scenario — the Cosmos DB hot-partition
   throttle or the expired TLS certificate — to show the agent reasoning across compute,
   data and networking failure modes, not just one.

#### Key moments

- **The approval gate** — the agent investigates end to end but stops, every time, at
  the decision.
- **Grounded evidence** — each step shows a real telemetry query and its result, not a
  chat answer pulled from nowhere.
- **Well-Architected mapping** — every incident ties back to a framework the audience
  likely already uses to score its own environment.

### 1.5 Anticipated questions

**"Is this connected to our real environment?"** — No. This is guided replay: six
deterministic, hand-authored transcripts. No live Azure calls are made and no action is
ever taken, so running it costs nothing and carries zero blast radius.

**"Could it take the action without approval?"** — Not in the **Review** mode shown
here: the agent proposes, and only an explicit human approval releases the action.
**Automatic** mode exists in the real product but is opt-in and separate from what this
demo shows.

**"Is our data used to train the AI models?"** — No, Azure OpenAI Service does not use
customer data to train the underlying models.

**"What would this cost to run for real?"** — The SRE Agent is billed in agent units;
chat is a billable operation, and an always-on agent accrues cost until it's **deleted**
(stopping it isn't enough). A pilot would set monthly caps and a cleanup runbook from day
one.

**"How would this connect to our alerting and ticketing tools?"** — The real agent
ingests signals from Azure Monitor and supports incident-management integrations;
choosing which signal sources and connectors matter for your environment is exactly what
a discovery workshop resolves.

**"Could we see it running live against our subscription?"** — Only against a
**dedicated sandbox agent**, under the strict rules in §2.5 — never production, and
never with approvals or writes enabled in anything shared or public.

### 1.6 From demo to next step

Propose a **scoped sandbox pilot**: stand up a dedicated SRE Agent against a
non-production subscription or resource group, wire in one or two real connectors (Log
Analytics / Application Insights), and replay a real historical incident to compare the
agent's investigation against what actually happened.

### 1.7 What this demo is not

All six investigations are hand-authored, deterministic transcripts — no live Azure
Monitor, Log Analytics or Application Insights calls happen, and no remediation is ever
executed; every approval shown is read-only. The Azure SRE Agent's data-plane API is in
public preview at the time of writing. A read-only live path against a dedicated sandbox
agent is scaffolded in the code but stays off unless deliberately configured (§2.5).

### Glossary

- **SRE Agent** — Microsoft's AI site-reliability agent for Azure workloads; investigates
  incidents and proposes remediations under configurable autonomy.
- **WAF (Well-Architected Framework)** — Microsoft's framework of pillars (Reliability,
  Security, Operational Excellence, Performance Efficiency, Cost Optimization) for
  evaluating workload design.
- **Review / ReadOnly / Automatic mode** — the agent's autonomy levels: Review requires
  human approval before acting, ReadOnly never acts, Automatic acts without approval
  (opt-in only).
- **Connector** — an integration the agent uses to query a telemetry or management
  source (e.g. Log Analytics, Application Insights, ARM).
- **RBAC** — role-based access control; who can administer, use or only read the agent.
- **Root cause** — the underlying condition that produced an incident's symptoms, as
  distinct from the symptoms themselves.
- **KQL (Kusto Query Language)** — the query language used against Log Analytics,
  Application Insights and Azure Data Explorer.
- **Control plane / data plane** — the control plane (ARM) manages the agent resource
  itself; the data plane exposes its threads, messages and approvals.

> *To prepare the environment for this demo, share Part 2 with your technical contact.*

---

## Part 2 · Technical Brief

### 2.1 Technical profile

| | |
|---|---|
| **Status** | Experimental |
| **Orchestration** | Human-in-the-loop; single agent, guided replay by default |
| **Models** | Managed entirely by the Azure SRE Agent service — this demo does not select or call a model directly |
| **Azure services** | Azure SRE Agent · Azure Monitor · Log Analytics · Application Insights (referenced/replayed; not called live by default) |
| **Stack** | FastAPI · vanilla HTML/JS · no IaC of its own (unified deploy only) |
| **Author** | @heblasco |

### 2.2 The architecture

```
Guided replay (default, always on — no Azure credentials needed):
Browser ── GET /api/scenarios ──────► scenarios.list_scenarios()   (6 seeded incidents)
Browser ── GET /api/scenarios/{id} ─► full investigation timeline
                                       (signal → tool query → agent reasoning → approval → resolution)
Browser ── GET /api/context ────────► capabilities + WAF notes + Microsoft Learn links
Browser ── GET /api/config ─────────► mode + rails (writes/approvals always false here) → drives the UI banner

Future live path (scaffolded, OFF until SRE_AGENT_RESOURCE_ID is deliberately set):
Browser ── same API shape ──► read-only proxy ──► dedicated SANDBOX Azure SRE Agent
                                  │ SSRF guard: only *.azuresre.ai, HTTPS
                                  │ writes + approvals forced off by default
                                  └ managed identity → ARM token + data-plane token
```

#### Components

| Component | Where | Role |
|---|---|---|
| Backend | [app/backend/main.py](app/backend/main.py) | FastAPI single container; serves the UI at `/` and the JSON API; reports `mode: replay` unless a live resource is configured |
| Scenario data | [app/backend/scenarios.py](app/backend/scenarios.py) | Six hand-authored, deterministic incident transcripts, plus the capabilities/WAF/doc-link content for the explainer panel |
| Config / live-path switches | [app/backend/config.py](app/backend/config.py) | Holds the (currently inactive) live-path settings and hard safety rails; replay mode needs none of them |
| Frontend | [app/frontend/](app/frontend/) | Vanilla HTML/JS — scenario picker, investigation timeline, capabilities panel |

#### The agents

| Agent | Kind | Model | Job |
|---|---|---|---|
| `sre-agent` | Replay: scripted transcript. Live path (future): the real Azure SRE Agent | Managed by the SRE Agent service | Investigates end to end — correlates the signal, queries telemetry connectors, determines root cause, proposes a reversible remediation |
| `approver` | Human, shown read-only | — | Reviews and approves/rejects the proposed action in Review mode; this demo never executes it |

### 2.3 Agentic patterns

| Pattern | Where in this demo | Why it matters here | In business terms |
|---|---|---|---|
| **Signal-driven investigation** | `role: "signal"` turns, [app/backend/scenarios.py](app/backend/scenarios.py) | The agent reacts to a monitoring alert rather than waiting for a human prompt, like a real on-call engineer | The system raises its own hand when something breaks |
| **Grounded, evidenced telemetry retrieval** | `role: "tool"` turns (real-shaped KQL queries) | Every hypothesis is checked against an actual query result before it's trusted | It shows its work, not just its conclusion |
| **Human-in-the-loop approval gate** | `role: "approval"` turns; `api_config()` forces `approvals_enabled: false` | The agent stops at the proposal — nothing executes without an explicit human decision | The agent drafts the fix; a person has to sign off |
| **Fail-closed live-path design** | `live_configured()`, SSRF allow-list, write/approval flags default `False` in [app/backend/config.py](app/backend/config.py) | A future live path only ever engages when fully and deliberately configured; every default is the safe one | Off is the default, not an accident waiting to happen |
| **Framework-anchored governance** | `WAF_NOTES` + per-scenario `waf` tags, [app/backend/scenarios.py](app/backend/scenarios.py) | Every incident ties back to Well-Architected pillars the audience already reports against | Speaks the reviewer's own scorecard |

### 2.4 Technical setup

Run before a session; the end state is what §1.4's presenter verification checks.

- [ ] `cd src/sre-agent-demo && pip install -r requirements.txt`
- [ ] Run: `uvicorn app.backend.main:app --port 8780` → http://localhost:8780
- [ ] No Azure credentials or environment variables are required — replay mode is the
  default and the only fully-supported mode today
- [ ] Confirm `/healthz` reports `mode: replay` and `/api/config` shows
  `writes_enabled: false`, `approvals_enabled: false`

### 2.5 Additional resources

#### API surface

| Method | Path | Description |
|---|---|---|
| GET | `/healthz` | Liveness + current mode |
| GET | `/api/config` | Mode + rails (writes/approvals off) — drives the UI banner |
| GET | `/api/scenarios` | List the six seeded incidents |
| GET | `/api/scenarios/{id}` | Full investigation timeline for one incident |
| GET | `/api/context` | Capabilities + WAF notes + doc links |

#### Deployment

Unified (AgentVerse portal) only — add an entry to `infra/demos.auto.tfvars` (one
`is_web` service, port `8780`, no `iac`, no `registration` block) — see
[docs/adding-a-demo.md](../../docs/adding-a-demo.md) and
`infra/demos.auto.tfvars.example`. Replay mode needs no injected environment variables.

#### Going live later (read-only, sandbox only)

The backend ([app/backend/config.py](app/backend/config.py)) already carries the
switches for a future read-only proxy to a **real** SRE Agent. It stays in replay mode
until `SRE_AGENT_RESOURCE_ID` is set. Any live path **must** honour these rules:

- **Dedicated sandbox agent only** — never point the demo at production. The real blast
  radius is the *agent's own* execution identity/connectors, so scope those to
  disposable resources and prefer `ReadOnly`/`Review` mode.
- **The iframe URL is reachable without the portal's auth** — an env flag is not
  authorization. Keep **approvals disabled** (`SRE_AGENT_ALLOW_APPROVALS=false`) and
  **writes disabled** (`SRE_AGENT_ALLOW_WRITE=false`) in any shared/public deploy; never
  expose broad thread listing (use a per-session or allow-listed thread).
- **Fail closed** — re-check `actionConfiguration.mode` before every mutation;
  missing/unknown mode disables writes; rely on `SRE Agent Reader` RBAC for the
  read-only guarantee, not just a flag.
- **SSRF guard** — only contact the ARM-returned `agentEndpoint` when its host ends
  with `.azuresre.ai` over HTTPS. Never accept raw agent/thread ids from the browser.
- **Auth** — the managed identity mints an ARM token and a data-plane token for audience
  `https://azuresre.dev/.default`; pre-assign it `SRE Agent Reader`/`User` on the agent
  scope (it cannot self-assign RBAC).
- **Cost** — chat is billable and an always-on flow accrues cost until the agent is
  **deleted** (`stop` is not enough); set monthly AAU caps and a cleanup runbook.
- **Don't hide breakage** — simulate only when deliberately unconfigured; if a live
  resource is configured but fails, surface "live integration unavailable" with a
  sanitized reason.

References: [API reference](https://learn.microsoft.com/azure/sre-agent/api-reference) ·
[Agent modes](https://learn.microsoft.com/azure/sre-agent/agent-modes) ·
[Pricing & billing](https://learn.microsoft.com/azure/sre-agent/pricing-billing) ·
[Well-Architected Framework](https://learn.microsoft.com/azure/well-architected/).
