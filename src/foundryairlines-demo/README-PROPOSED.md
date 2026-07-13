> **📐 Proposal.** A self-contained, standardized README following the AgentVerse
> [template](../templates/demo-scaffold/README-TEMPLATE.md), offered for the demo author
> to adopt — and adapt — as this demo's README.

---

# FoundryAirlines

> Three AI agents that fill low-occupancy flights with event-aware promotional
> banners — an accessible first demonstration of multi-agent orchestration.

<img width="1496" height="908" alt="FoundryAirlines front-end showing the agent run and generated banners" src="https://github.com/user-attachments/assets/e69bc73e-7af4-45c3-85d0-555937f2388c" />

**Contents:** [Part 1 · Business Brief](#part-1--business-brief) — present the demo ·
[Part 2 · Technical Brief](#part-2--technical-brief) — prepare and operate it

---

## Part 1 · Business Brief

### 1.1 At a glance

| | |
|---|---|
| **Scenario** | Airline revenue & marketing — recovering revenue from flights departing with empty seats |
| **Business outcome** | A targeted, event-aware promotional campaign produced in minutes instead of days |
| **Best suited for** | A first conversation about AI agents; marketing, revenue-management or innovation audiences |
| **Duration** | ~10 minutes |
| **Presenter effort** | A technical co-presenter is recommended for fully live runs; solo presentation is viable using cached mode |
| **Demo reliability** | Live cloud demo — every run makes real model, web-search and image-generation calls; the image step is the slowest and most variable |
| **Contingency** | Add `?cached=1` to the page address to replay the banners generated during the warm-up run |

### 1.2 The story

An airline is flying half-empty planes. The revenue team can see exactly which flights
have the lowest occupancy — the data sits in their bookings database — but turning that
insight into a targeted promotion is slow, manual work: someone has to pick the flights,
research what is happening in each destination that would attract a traveler, and brief
a designer for the creative. By the time the campaign ships, the flight has departed.

This demo compresses that whole chain into one click. A **flights agent** queries the
bookings database and picks the five emptiest flights. An **events agent** then searches
the live web and finds one *real, upcoming* event in each destination city around the
flight date — a festival, a match, an exhibition. Finally, an image model generates a
promotional banner per flight that combines the fare and date with the event it found.

Why agents and not a script? Because two of the three steps require judgment and live
knowledge a script cannot have: deciding which event a traveler would actually fly for,
grounded in today's web — and composing marketing creative from it. The deterministic
part (querying the database) stays deterministic; the agents sit only where reasoning
lives.

### 1.3 The business case

| Business KPI | Without agents | Impact demonstrated |
|---|---|---|
| **Load factor on underperforming flights** | Low-occupancy flights are identified in reports but rarely receive a dedicated, timely campaign | The pipeline targets precisely the 5 lowest-occupancy flights, automatically and on demand |
| **Campaign time-to-market** | Days: analyst selection → destination research → designer brief → creative review | Minutes: from database rows to finished, event-aware creative in a single run |
| **Creative production cost per campaign** | A designer round-trip per destination and offer | Generated banners per flight; human review shifts from production to approval |
| **Offer relevance / expected conversion** | Generic discount messaging per route | Each offer is anchored to a verifiable, upcoming local event found on the live web, with a source link |

The KPI that carries the argument is **time-to-market**: the value of a promotion for a
flight departing within weeks decays daily, so compressing the campaign cycle from days
to minutes is what converts existing occupancy insight into recoverable revenue. The
pattern generalizes to any business with perishable inventory and local context — hotel
rooms, event tickets, retail seasonality.

### 1.4 Delivering the demo

#### Presenter verification (5 minutes before)

- [ ] The demo page opens at the address provided by your technical contact and shows the FoundryAirlines interface
- [ ] A complete warm-up run was executed earlier the same day (this also confirms cloud sign-in is current and leaves banners available for cached mode)
- [ ] You know the page address variant for cached mode (`?cached=1`)

#### Demonstration sequence

1. *(0–2 min, technical rooms only — skip for business audiences)* Show the two agents
   living in the Azure AI Foundry portal and exchange one message with the events agent:
   these are persistent cloud agents that can be inspected and tested independently.
2. *(2–4 min)* Start a run from the demo page. As the first results appear: *"the system
   has just identified the five flights departing with the most empty seats — the revenue
   we are currently losing."*
3. *(4–6 min)* Pause on the events results: each destination has received a *real*
   upcoming event with a source link. Open one link. *"This was found on the live web
   seconds ago — it is verifiable, not invented."*
4. *(6–8 min)* The banner generation takes one to two minutes. Use this window for the
   business case (§1.3): what a campaign cycle costs today, and what it means to run one
   per day instead of one per quarter.
5. *(8–10 min)* Close on the five finished banners combining fare, date and the
   discovered event: *"from database rows to a ready-to-review campaign, in one click."*

#### Key moments

- The **source link** on each event — grounded, verifiable, and retrieved seconds earlier.
- The **banners appearing** — the complete campaign cycle, compressed into one run.

### 1.5 Anticipated questions

**"Is our data used to train the AI models?"** — No. Azure OpenAI Service does not use
customer data to train the underlying models; prompts and outputs stay within the
customer's Azure tenant boundary.

**"Are those events real?"** — Yes. The events agent searches the live web at run time
and returns a source link with each result; any of them can be opened and checked during
the session. If no suitable event is found for a destination, the agent says so and
falls back to a generic cultural highlight rather than inventing one.

**"What does a run like this cost?"** — Each run makes a handful of language-model calls
and five image generations — consumption-priced, typically well under a euro per run.
Production-scale costs depend on volume and are exactly what a pilot scopes.

**"Would this work with our inventory and our brand?"** — The pattern — perishable
inventory + live local context + generated creative — transfers directly. Brand control
(templates, tone, review workflows) is one of the first things a real deployment adds;
see §1.7.

**"How long would a pilot take?"** — This demo was built in days. A scoped pilot against
one real data source is typically a matter of weeks, not months — the discovery workshop
(§1.6) is where that gets sized honestly.

### 1.6 From demo to next step

Propose a short **envisioning session**: identify the customer's perishable inventory,
the data source that already knows what is underperforming, and the local context that
would make an offer compelling. Output: one candidate use case and the data access
needed for a scoped pilot.

### 1.7 What this demo is not

The bookings database is simulated (a local sample database, not a real reservation
system). Generated banners go straight to screen — a real deployment would add brand
templates, content review and approval workflows before anything reaches a customer.
The demo status is beta: it is a teaching and demonstration asset, not a campaign
product.

### Glossary

- **AI agent** — a model given a role, instructions and tools, able to decide how to
  complete a task rather than following a fixed script.
- **Azure AI Foundry** — the Azure platform where the agents are created, hosted and
  can be individually tested.
- **Grounding** — connecting an agent to a live source (here: web search) so its answers
  come from current, citable data rather than the model's memory.
- **Orchestration** — coordinating several agents so each one's output feeds the next.
- **Cached mode** — replaying the banners from an earlier run instead of generating new
  ones; used for time-constrained or contingency presentations.

> *To prepare the environment for this demo, share Part 2 with your technical contact.*

---

## Part 2 · Technical Brief

### 2.1 Technical profile

| | |
|---|---|
| **Status** | Beta |
| **Orchestration** | Sequential (MAF `WorkflowBuilder`) |
| **Models** | gpt-4.1 · gpt-image-2 |
| **Azure services** | Azure AI Foundry (agents + Bing Grounding + image deployment) |
| **Stack** | Microsoft Agent Framework · FastAPI + SSE · vanilla HTML/JS · Terraform |
| **Runs locally without Azure?** | No — the agents, Bing Grounding and image generation are all cloud calls |
| **Author** | — |

### 2.2 The architecture

The workflow end to end:

```
┌────────────────────── MAF WorkflowBuilder (sequential) ──────────────────────┐
│                                                                              │
│   ┌─────────────────┐         ┌────────────────────┐                         │
│   │ FlightsExecutor │ ──────► │  EventsExecutor    │                         │
│   │  (wraps the     │  msgs   │  (wraps the        │                         │
│   │  flights-agent) │         │   events-agent +   │                         │
│   └─────────────────┘         │   Bing Grounding)  │                         │
│           │                   └─────────┬──────────┘                         │
│           │ ctx.add_event               │ ctx.add_event / yield_output       │
└───────────┼─────────────────────────────┼─────────────────────────────────────┘
            ▼                             ▼
       ┌────────────────────────────────────────────┐
       │  Backend SSE stream  (FastAPI, port 8765)  │
       └─────────────────────┬──────────────────────┘
                             ▼
                   ┌──────────────────────┐
                   │ gpt-image-2 (Agent 3)│
                   │  generates 5 PNG     │
                   │  banners concurrent. │
                   └──────────────────────┘
```

#### Components

| Component | Where | Role |
|---|---|---|
| MAF sequential workflow | [app/backend/agents.py](app/backend/agents.py) | Two `Executor`s wrapping the persistent Foundry agents, chained with `WorkflowBuilder.add_edge` |
| Agent bootstrap | [app/backend/bootstrap_agents.py](app/backend/bootstrap_agents.py) | Idempotently creates the two persistent prompt agents in the Foundry project |
| Backend | [app/backend/main.py](app/backend/main.py) | FastAPI; streams workflow progress over Server-Sent Events |
| Front-end | [app/frontend/](app/frontend/) | Vanilla HTML/JS, yellow/white/grey; renders the stream and the banners |
| Bookings DB | SQLite (seeded by [app/backend/seed_db.py](app/backend/seed_db.py)) | The "internal system" the flights agent reads |
| Infra | [infra/main.tf](infra/main.tf) | Terraform for the Foundry account, project, model deployments and Bing resource |

#### The agents

| Agent | Kind | Model | Job |
|---|---|---|---|
| `flights-agent` | Foundry prompt agent (persistent) | gpt-4.1 | Turns raw bookings rows into the 5 lowest-occupancy flights as strict JSON |
| `events-agent` | Foundry prompt agent + Bing Grounding tool | gpt-4.1 | Finds one real upcoming event per destination city, with a source URL |
| Banner step | Direct Azure OpenAI call (not an agent) | gpt-image-2 | Generates a wide promotional PNG per flight — image models do not fit the executor pattern, so this is a deliberate direct call |

### 2.3 Agentic patterns

| Pattern | Where in this demo | Why it matters here | In business terms |
|---|---|---|---|
| **Sequential orchestration** | `WorkflowBuilder(...).add_edge(...)` in [app/backend/agents.py](app/backend/agents.py) | The canonical first pattern: each agent's output is the next agent's input | An assembly line of specialists, each finishing the previous one's work |
| **Persistent (server-side) agents** | [app/backend/bootstrap_agents.py](app/backend/bootstrap_agents.py) | The agents live in the Foundry project and can be opened and tested in the portal | The specialists exist in the cloud and can be interviewed individually |
| **Tool use / web grounding** | Bing Grounding attached as a persistent tool on `events-agent` | The events are real — the agent cites the live web, not its training data | The agent looks things up and shows its sources |
| **Structured JSON contracts** | Both agents' instructions demand "ONLY a JSON array" | Reliable machine-to-machine hand-off; no prose parsing | The specialists exchange forms, not conversations |
| **Streaming progress (SSE)** | `ctx.add_event` → [app/backend/sse.py](app/backend/sse.py) | The audience observes each agent's contribution as it happens | You watch the work happen instead of waiting for a result |
| **Combining agents with non-agent model calls** | The gpt-image-2 banner step | Shows precisely where the agent abstraction ends | Not everything needs to be an agent — some steps are simply a service call |

### 2.4 Technical setup

Run the day before a session; the end state is what §1.4's presenter verification
checks.

- [ ] Azure resources in place: a Foundry (AI Services) account + project, `gpt-4.1` and
      `gpt-image-2` deployments, and a Bing Grounding resource — provisioned via
      [infra/](infra/) (Terraform) or the Azure CLI. Pick a region with quota for both
      models (**eastus2** is the safest choice today)
- [ ] One-time portal step: connect the Bing resource to the Foundry project as a
      **Grounding with Bing Search** connection named `bing-grounding` (Management
      center → Connected resources → + New connection). The management API currently
      returns HTTP 500 for new projects; the portal works
- [ ] `az login`; copy `app/.env.example` to `app/.env` and fill in `PROJECT_ENDPOINT`,
      `IMAGE_ENDPOINT`, `IMAGE_DEPLOYMENT`, `BING_CONNECTION_NAME`
- [ ] `pip install -r requirements.txt`; then `python -m app.backend.bootstrap_agents`
      (idempotent; `--reset` deletes and recreates the two prompt agents)
- [ ] `uvicorn app.backend.main:app --port 8765`; open `app/frontend/index.html`
- [ ] Execute one full warm-up run — warms gpt-image-2, confirms credentials, and populates `app/output/` for cached mode

Known failure modes: *`No Foundry connection named 'bing-grounding'`* → the portal
connection step above was skipped; *image step returns 429/503* → gpt-image-2 is
rate-limited, the code retries 6× with backoff — re-run or fall back to cached mode;
*`DefaultAzureCredential` errors* → `az login` again.

### 2.5 Additional resources

#### A second variant: City Activities Poster

The repository also ships an undocumented variant: [app/backend/city_agents.py](app/backend/city_agents.py)
plus [app/frontend_city/](app/frontend_city/) and its own bootstrap
([app/backend/bootstrap_city_agents.py](app/backend/bootstrap_city_agents.py)). Given a
city name, a Bing-grounded `activities-agent` finds real attractions and gpt-image-2
renders a travel poster. Same patterns, single-agent — suitable as an additional
demonstration if time allows.

#### Reproduce the agents by hand

Each prompt agent can be recreated standalone in the Foundry portal: create a Prompt
Agent on `gpt-4.1` with the exact instructions found in
[app/backend/bootstrap_agents.py](app/backend/bootstrap_agents.py) (for the events
agent, additionally attach the Bing Grounding tool). CLI runners exercise each agent in
isolation: `python -m app.scripts.run_flights_agent` and
`python -m app.scripts.run_events_agent` — useful as a workshop exercise.

#### Manifest and license

Catalog manifest: [agentverse.yaml](agentverse.yaml). License: MIT.
