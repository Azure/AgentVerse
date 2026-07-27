# FoundryAirlines — 3-agent demo on Azure AI Foundry

A small but realistic demo showing how to **orchestrate three Foundry agents
sequentially** with the Microsoft Agent Framework (MAF) `WorkflowBuilder`.

<img width="1496" height="908" alt="image" src="https://github.com/user-attachments/assets/e69bc73e-7af4-45c3-85d0-555937f2388c" />



| Step | Agent | Foundry asset | What it does |
|------|-------|---------------|--------------|
| 1 | `flights-agent` | Foundry **prompt agent** | Reads a local SQLite "bookings" DB, picks the 5 flights with the lowest occupancy, and returns a strict JSON array. |
| 2 | `events-agent`  | Foundry **prompt agent** + **Bing Grounding** tool | For each flight, searches the live web with Bing Grounding to find one real upcoming event in the destination city around the flight date. |
| 3 | `gpt-image-2`   | Azure OpenAI deployment | Generates a wide PNG promo banner per flight that mixes the flight's price/date with the event found in step 2. |

The first two agents live in your Foundry project (you can open them in the
portal and chat with them by hand). The third step is a direct call to the
`gpt-image-2` deployment — image models are not chat agents, so they don't
fit the executor pattern.

The orchestration follows the official sequential pattern:
- https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/sequential
- https://github.com/dsanchor/agents-observability-tt202/blob/main/from-zero-to-hero/orchestration/demo/sequential_agents.py

A small FastAPI backend streams progress over Server-Sent Events to a vanilla
HTML/JS front-end styled in yellow / white / grey.

---

## Architecture

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

---

## Prerequisites

- An Azure subscription with permission to create resources (Owner or
  Contributor + User Access Administrator).
- Azure CLI ≥ 2.60 (`az login`).
- Python 3.11+.
- Quota for `gpt-4.1` and `gpt-image-2` in your Foundry region. **eastus2**
  is the safest pick today — it has both.

The whole demo lives in **one** Foundry account / project so there's nothing
to wire across regions.

---

## 1 · Create the Azure resources

Pick names you like. The values below are placeholders — replace `<…>` with
your own.

```bash
LOCATION=eastus2
RG=<your-resource-group>
FOUNDRY_ACCOUNT=<your-foundry-account>     # globally-unique, lowercase, ≤ 24 chars
PROJECT=<your-project-name>
BING_RESOURCE=<your-bing-resource>          # globally-unique, lowercase

# 1. Resource group
az group create -n "$RG" -l "$LOCATION"

# 2. Foundry (AI Services) account — single account, kind=AIServices
#    Reference: https://learn.microsoft.com/en-us/azure/foundry/tutorials/quickstart-create-foundry-resources
az cognitiveservices account create \
  -n "$FOUNDRY_ACCOUNT" -g "$RG" -l "$LOCATION" \
  --kind AIServices --sku S0 \
  --custom-domain "$FOUNDRY_ACCOUNT" \
  --assign-identity --yes

# 3. Foundry project (created via the data plane)
ENDPOINT="https://${FOUNDRY_ACCOUNT}.services.ai.azure.com"
TOKEN=$(az account get-access-token --resource https://ai.azure.com --query accessToken -o tsv)
curl -s -X PUT \
  "${ENDPOINT}/api/projects/${PROJECT}?api-version=2025-05-15-preview" \
  -H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" \
  -d '{"properties":{"displayName":"'"${PROJECT}"'"}}'

# 4. Deploy the chat model used by both prompt agents
az cognitiveservices account deployment create \
  -n "$FOUNDRY_ACCOUNT" -g "$RG" \
  --deployment-name gpt-4.1 \
  --model-name gpt-4.1 --model-version "2025-04-14" --model-format OpenAI \
  --sku-capacity 50 --sku-name GlobalStandard

# 5. Deploy gpt-image-2 (used by the banner step)
az cognitiveservices account deployment create \
  -n "$FOUNDRY_ACCOUNT" -g "$RG" \
  --deployment-name gpt-image-2 \
  --model-name gpt-image-2 --model-version "2025-09-15" --model-format OpenAI \
  --sku-capacity 1 --sku-name GlobalStandard

# 6. Bing Grounding resource (used by Agent 2)
az resource create -g "$RG" -n "$BING_RESOURCE" \
  --resource-type "Microsoft.Bing/accounts" --location global \
  --is-full-object \
  --properties '{"sku":{"name":"G1"},"kind":"Bing.Grounding"}'
```

> If `gpt-image-2` is not available in your subscription/region, request
> access in the [Foundry catalog](https://ai.azure.com/catalog/models/gpt-image-2)
> and pick a region that lists it.

---

## 2 · Connect Bing Grounding to your project (one-time portal step)

> **Known platform issue.** Creating this connection through the management
> API currently returns **HTTP 500** from `credential.vienna-eastus2.svc/...:putbatch`
> for new Foundry projects. The portal works fine. Do this step once in the
> UI and you're done.

1. Open https://ai.azure.com → select your project.
2. **Management center** (bottom-left) → **Connected resources** → **+ New connection**.
3. Choose **Grounding with Bing Search**.
4. Pick the Bing resource you created in step 6 above.
5. Name the connection **`bing-grounding`** (or whatever you set in
   `BING_CONNECTION_NAME`, see below).

The bootstrap script reads this connection by name and attaches it as a
**persistent tool** on the events-agent. Once attached, the tool is visible
in the Foundry portal under **Agents → events-agent → Tools** and you can
chat with the agent by hand to test it.

Reference: https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/bing-tools

---

## 3 · Configure and install the app

```bash
git clone <this-repo>
cd <repo-folder>

# Python deps
python -m venv .venv
. .venv/bin/activate                     # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Azure auth — DefaultAzureCredential picks up your `az login` identity
az login

# App config
cp app/.env.example app/.env
# Edit app/.env and fill in PROJECT_ENDPOINT, IMAGE_ENDPOINT, etc.
```

`app/.env` template:

```
PROJECT_ENDPOINT=https://<your-foundry-account>.services.ai.azure.com/api/projects/<your-project>
MODEL_DEPLOYMENT_NAME=gpt-4.1
BING_CONNECTION_NAME=bing-grounding
IMAGE_ENDPOINT=https://<your-foundry-account>.openai.azure.com
IMAGE_DEPLOYMENT=gpt-image-2
IMAGE_API_VERSION=2025-04-01-preview
```

---

## 4 · Bootstrap the two persistent prompt agents

```bash
python -m app.backend.bootstrap_agents          # idempotent
python -m app.backend.bootstrap_agents --reset  # delete and recreate
```

This creates two `PromptAgentDefinition` agents in your Foundry project. They
**persist** server-side and are visible in the portal at **Agents**.

You can:
- chat with each agent in the portal to test it,
- call them from any other client (their names live in `app/agents.json`),
- delete them with `--reset` and recreate them.

---

## 5 · Run the demo

```bash
# Backend (SSE on http://127.0.0.1:8765)
uvicorn app.backend.main:app --port 8765

# Front-end — just open the page; it points at the backend on the same host
open app/frontend/index.html
```

`?cached=1` reuses any banners already present in `app/output/` — useful for
back-to-back demos. Drop the flag for a fresh end-to-end run (~60–120 s for
the banner step).

---

## How the agents are orchestrated (MAF, sequential)

```python
# app/backend/agents.py — abridged
from agent_framework import (
    ChatMessage, Executor, Role, WorkflowBuilder, WorkflowContext,
    WorkflowOutputEvent, handler,
)
from agent_framework.azure import AzureAIAgentClient

class FlightsExecutor(Executor):
    @handler
    async def handle(self, msg: ChatMessage,
                     ctx: WorkflowContext[list[ChatMessage]]) -> None:
        rows = query_low_occupancy_flights(5)
        resp = await self._agent.run(ChatMessage(role=Role.USER,
                                                 text=json.dumps(rows)))
        await ctx.send_message([msg, *resp.messages])

class EventsExecutor(Executor):
    @handler
    async def handle(self, history: list[ChatMessage],
                     ctx: WorkflowContext[None, list[ChatMessage]]) -> None:
        ask = ChatMessage(role=Role.USER, text="Find one real event per flight…")
        resp = await self._agent.run([*history, ask])
        await ctx.yield_output([*history, ask, *resp.messages])

workflow = (
    WorkflowBuilder(name="FoundryAirlinesSequential",
                    start_executor=flights_exec)
        .add_edge(flights_exec, events_exec)
        .build()
)
async for event in workflow.run_stream(trigger):
    ...
```

`AzureAIAgentClient` wraps the **persistent** Foundry prompt agent created
by `bootstrap_agents.py`, so the executors run server-side prompt agents —
not local-only ones.

---

## Reproduce Agent 1 (`flights-agent`) standalone

In the Foundry portal, create a Prompt Agent with model `gpt-4.1` and these
exact instructions (also in `app/backend/bootstrap_agents.py`):

```
You are a revenue analyst for an airline. The user message contains a JSON
array of raw flight rows from the internal flights database.

Return ONLY a JSON array (no prose, no code fences) preserving each row and
exposing exactly these fields per flight:

  - id                  (integer, original row id)
  - code                (flight code, e.g. "VY1234")
  - origin              (IATA code)
  - destination         (IATA code)
  - destination_city    (string)
  - destination_country (string)
  - date                (YYYY-MM-DD)
  - occupancy_pct       (one decimal)
  - price_eur           (integer euros)

Order the array by occupancy_pct ascending (lowest occupancy first).
```

Test it by pasting any JSON array of flight-shaped rows into the chat.

You can also run it from the CLI:

```bash
python -m app.scripts.run_flights_agent
```

---

## Reproduce Agent 2 (`events-agent`) standalone

Same procedure as Agent 1 but **attach the Bing Grounding tool** in the
portal (Agents → + Tool → Grounding with Bing Search → pick `bing-grounding`).

Instructions:

```
You are a cultural concierge for an airline. The conversation history contains
a JSON array of flights with destination_city, destination_country and date.

For EACH flight, use the Bing Grounding tool to search the live web for ONE
real, public, upcoming event in that city around that date — for example
festivals, concerts, sports matches, exhibitions, conferences. Prefer events
that are well-documented and that a traveler could actually attend.

Return ONLY a JSON array (no prose, no code fences) with the same length and
ordering as the input flights. Each element must have:

  - flight_id         (integer matching the input)
  - title             (max 8 words, the event name)
  - short_description (max 14 words, what it is and when)
  - source_url        (the Bing search result URL you trusted)

If you cannot find a real event for a flight, set title to "Local highlights"
and short_description to a generic one-line cultural pitch for that city, and
set source_url to an empty string.
```

CLI run:

```bash
python -m app.scripts.run_events_agent
```

---

## Repository layout

```
app/
  backend/
    main.py                # FastAPI + SSE
    agents.py              # MAF WorkflowBuilder + executors
    bootstrap_agents.py    # creates the two persistent prompt agents
  frontend/
    index.html             # vanilla HTML + JS, yellow/white/grey theme
  data/
    flights.db             # SQLite "bookings" DB used by Agent 1
  output/                  # generated banners land here
  .env.example             # copy to .env and fill in
requirements.txt
```

---

## Troubleshooting

- **`No Foundry connection named 'bing-grounding'`** — finish step 2 (portal).
- **Image step fails with 429 / 503** — `gpt-image-2` is rate-limited; the
  code retries 6× with backoff. Re-run, or pre-warm with `?cached=0`.
- **`PROJECT_ENDPOINT` not set** — copy `.env.example` to `.env` and fill it
  in.
- **`DefaultAzureCredential` errors** — `az login` again, then re-run.

---

## License

MIT.
