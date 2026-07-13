> **📐 Proposed standardized README.** This file follows the AgentVerse standard demo
> presentation structure ([template](../templates/demo-scaffold/README-TEMPLATE.md)).
> The author's original [README.md](README.md) remains the canonical documentation —
> all setup detail lives there; this file organizes the demo for presentation.

---

# FoundryAirlines

> Three Foundry agents that fill low-occupancy flights with event-aware promotional
> banners — an accessible introduction to sequential multi-agent orchestration with MAF.

| | |
|---|---|
| **Industry / scenario** | Airline · revenue & marketing |
| **Audience** | Teams new to Azure AI Foundry agents and MAF workflows |
| **Status** | Beta |
| **Difficulty** | Beginner |
| **Orchestration** | Sequential (MAF `WorkflowBuilder`) |
| **Models** | gpt-4.1 · gpt-image-2 |
| **Azure services** | Azure AI Foundry (agents + Bing Grounding + image deployment) |
| **Stack** | Microsoft Agent Framework · FastAPI + SSE · vanilla HTML/JS · Terraform |
| **Runs locally without Azure?** | No — the agents, Bing Grounding and image generation are all cloud calls (banners can be replayed with `?cached=1`) |
| **Author & original docs** | [README.md](README.md) |

---

## 1 · The story

An airline is flying half-empty planes. The revenue team can see exactly which flights
have the lowest occupancy — the data sits in their bookings database — but turning that
insight into a targeted promotion is slow, manual work: someone has to pick the flights,
research what is happening in each destination that would attract a traveler, and brief
a designer for the creative. By the time the campaign ships, the flight has departed.

This demo compresses that whole chain into one click. A **flights agent** queries the
bookings DB and picks the five emptiest flights. An **events agent** then searches the
live web (Bing Grounding) and finds one *real, upcoming* event in each destination city
around the flight date — a festival, a match, an exhibition. Finally, **gpt-image-2**
generates a wide promotional banner per flight that combines the fare and date with the
event it found.

Why agents and not a script? Because two of the three steps require judgment and live
knowledge a script cannot have: deciding which event a traveler would actually fly for,
grounded in today's web — and composing marketing creative from it. The deterministic
part (querying the DB) stays deterministic; the agents sit only where reasoning lives.

The demo is deliberately small: two persistent prompt agents that can be opened and
tested in the Foundry portal, one image deployment, one sequential workflow. It is the
recommended first demo for an audience new to AgentVerse.

---

## 2 · The business case

The demo speaks to airline revenue management and marketing: perishable inventory
(an empty seat at departure is revenue lost forever) served by a campaign process too
slow to react to it.

| Business KPI | Without agents | Impact demonstrated |
|---|---|---|
| **Load factor on underperforming flights** | Low-occupancy flights are identified in reports but rarely receive a dedicated, timely campaign | The pipeline targets precisely the 5 lowest-occupancy flights, automatically and on demand |
| **Campaign time-to-market** | Days: analyst selection → destination research → designer brief → creative review | Minutes: from database rows to finished, event-aware creative in a single run |
| **Creative production cost per campaign** | A designer round-trip per destination and offer | Generated banners per flight; human review shifts from production to approval |
| **Offer relevance / expected conversion** | Generic discount messaging per route | Each offer is anchored to a verifiable, upcoming local event found on the live web, with a source URL |

The KPI that carries the argument is **time-to-market**: the value of a promotion for a
flight departing within weeks decays daily, so compressing the campaign cycle from days
to minutes is what converts existing occupancy insight into recoverable revenue.

---

## 3 · The architecture

The original diagram in [README.md](README.md#architecture) shows the full flow; in
summary:

```
flights-agent ──► events-agent (+ Bing Grounding) ──► gpt-image-2 banners
      └────────── MAF WorkflowBuilder (sequential) ─────────┘
                             │ ctx.add_event / yield_output
                             ▼
              FastAPI backend — SSE stream (port 8765)
                             ▼
                 vanilla HTML/JS front-end
```

### Components

| Component | Where | Role |
|---|---|---|
| MAF sequential workflow | [app/backend/agents.py](app/backend/agents.py) | Two `Executor`s wrapping the persistent Foundry agents, chained with `WorkflowBuilder.add_edge` |
| Agent bootstrap | [app/backend/bootstrap_agents.py](app/backend/bootstrap_agents.py) | Idempotently creates the two persistent prompt agents in the Foundry project |
| Backend | [app/backend/main.py](app/backend/main.py) | FastAPI; streams workflow progress over Server-Sent Events |
| Front-end | [app/frontend/](app/frontend/) | Vanilla HTML/JS, yellow/white/grey; renders the stream and the banners |
| Bookings DB | SQLite (seeded by [app/backend/seed_db.py](app/backend/seed_db.py)) | The "internal system" the flights agent reads |
| Infra | [infra/main.tf](infra/main.tf) | Terraform for the Foundry account, project, model deployments and Bing resource |

### The agents

| Agent | Kind | Model | Job |
|---|---|---|---|
| `flights-agent` | Foundry prompt agent (persistent) | gpt-4.1 | Turns raw bookings rows into the 5 lowest-occupancy flights as strict JSON |
| `events-agent` | Foundry prompt agent + Bing Grounding tool | gpt-4.1 | Finds one real upcoming event per destination city, with a source URL |
| Banner step | Direct Azure OpenAI call (not an agent) | gpt-image-2 | Generates a wide promotional PNG per flight — image models do not fit the executor pattern, so this is a deliberate direct call |

---

## 4 · Agentic patterns

| Pattern | Where in this demo | Why it matters here |
|---|---|---|
| **Sequential orchestration** | `WorkflowBuilder(...).add_edge(flights_exec, events_exec)` in [app/backend/agents.py](app/backend/agents.py) | The canonical first pattern: each agent's output is the next agent's input |
| **Persistent (server-side) agents** | [app/backend/bootstrap_agents.py](app/backend/bootstrap_agents.py) | The agents live in the Foundry project — they can be opened and tested in the portal, which is itself a demonstration step |
| **Tool use / web grounding** | Bing Grounding attached as a persistent tool on `events-agent` | The events are *real* — the agent cites the live web, not its training data |
| **Structured JSON contracts** | Both agents' instructions demand "ONLY a JSON array" | Reliable machine-to-machine hand-off between agents; no prose parsing |
| **Streaming progress (SSE)** | `ctx.add_event` → [app/backend/sse.py](app/backend/sse.py) | The audience observes each agent's contribution as it happens |
| **Combining agents with non-agent model calls** | The gpt-image-2 banner step | Shows precisely where the agent abstraction ends — a useful teaching point |

---

## 5 · Demonstration guide

**Duration:** ~10 min · **Requires Azure live:** yes — keep `?cached=1` available as a
contingency to replay previously generated banners.

### Preparation checklist

- [ ] `az login` completed; `app/.env` filled in (see [README.md §3](README.md#3--configure-and-install-the-app))
- [ ] Agents bootstrapped: `python -m app.backend.bootstrap_agents`
- [ ] Backend running: `uvicorn app.backend.main:app --port 8765`
- [ ] Front-end open (`app/frontend/index.html`)
- [ ] One full run executed before the session — it warms gpt-image-2 and leaves banners in `app/output/` for the `?cached=1` contingency

### Demonstration sequence

1. *(Recommended)* Open the Foundry portal → **Agents** and show that `flights-agent`
   and `events-agent` exist server-side; exchange one message with `events-agent` to
   establish that these are persistent cloud agents, not local code.
2. In the front-end, start a run. As the flights agent returns, point out the five
   lowest-occupancy flights delivered as strict JSON — the structured contract between
   agents.
3. Pause on the events agent's output: each destination receives a *real* upcoming event
   with a source URL. Open one link to establish that the result is grounded in the live
   web rather than generated from memory.
4. The banner step takes 60–120 seconds; use this interval to walk through the
   sequential workflow code ([README.md's snippet](README.md#how-the-agents-are-orchestrated-maf-sequential)).
5. Conclude with the five generated banners combining fare, date and the discovered
   event — from database rows to finished creative in a single run.

### Key moments

- The **source URL** on each event — grounded, verifiable, and retrieved seconds earlier.
- The **generated banners** — the complete campaign cycle, compressed into one click.

---

## 6 · Additional resources

### A second variant: City Activities Poster

The repository also ships an undocumented variant: [app/backend/city_agents.py](app/backend/city_agents.py)
plus [app/frontend_city/](app/frontend_city/) and its own bootstrap
([app/backend/bootstrap_city_agents.py](app/backend/bootstrap_city_agents.py)). Given a
city name, an `activities-agent` (Bing-grounded) finds real attractions and gpt-image-2
renders a travel poster. Same patterns, single-agent — suitable as an additional
demonstration if time allows.

### Reproduce the agents by hand

[README.md](README.md#reproduce-agent-1-flights-agent-standalone) includes the exact
portal instructions to recreate each prompt agent standalone, plus CLI runners
(`python -m app.scripts.run_flights_agent`, `run_events_agent`) — useful as a workshop
exercise.

### Setup, deployment and troubleshooting

All in the canonical [README.md](README.md): Azure resource creation (az CLI, steps 1–5),
the one-time Bing connection portal step, `.env` reference, and a troubleshooting table
covering the known failure modes (missing Bing connection, gpt-image-2 rate limits,
credential expiry). [infra/](infra/) holds the Terraform equivalent. The catalog manifest
is [agentverse.yaml](agentverse.yaml). License: MIT.
