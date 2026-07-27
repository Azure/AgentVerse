# Model Evaluator

> Send one prompt to two Azure AI Foundry models in parallel and compare latency,
> tokens and quality side by side — with an optional blind AI judge.

**Contents:** [Part 1 · Business Brief](#part-1--business-brief) — present the demo ·
[Part 2 · Technical Brief](#part-2--technical-brief) — prepare and operate it

---

## Part 1 · Business Brief

### 1.1 At a glance

| | |
|---|---|
| **Scenario** | AI platform engineering — deciding which Foundry model deployment to use for a workload |
| **Business outcome** | A fair, side-by-side comparison of two candidate models on the same prompt — latency, tokens, and an optional quality verdict — in under a minute |
| **Best suited for** | Platform engineering, AI/ML leads and technical buyers deciding which model(s) to standardize on |
| **Duration** | ~5 minutes |
| **Presenter effort** | Solo-friendly for a technical audience; helps to be able to explain the metrics |
| **Demo reliability** | Good — this makes real calls to live models, so exact numbers vary run to run by design; the mechanism is always the same |
| **Contingency** | Have a prior exported comparison (JSON/CSV) on hand in case a live model is briefly unavailable |

### 1.2 The story

Every team with access to Azure AI Foundry ends up with more model deployments than
anyone has rigorously compared. A new model ships, someone deploys it, and then the
question "should we switch?" gets answered by one engineer's anecdotal impression in a
notebook — or not answered at all, and the team just keeps paying for whatever they
started with.

This demo turns that guess into a one-minute, side-by-side measurement. Pick any two
chat-capable deployments from a dropdown that is discovered live from the team's own
Foundry project — deploy a new model and it shows up on refresh, nothing to configure.
Send both the same prompt at the same time and watch them stream back in parallel, with
latency, time-to-first-token, token counts and throughput measured fairly, on equal
footing. An explicit, optional action then asks a third model to blindly judge both
answers — never knowing which model produced which, and never the model being compared
— and scores them on a fixed rubric.

Why does this need an agent-style approach rather than a fixed benchmark script? Because
"which answer is better" is a judgment call, not an arithmetic one — that's exactly what
an LLM judge is for, provided its own biases (position, self-preference) are actively
designed against rather than ignored. The rest is disciplined plumbing: identical
inputs, a shared clock, and a report that shows its work.

### 1.3 The business case

| Business KPI | Without agents | Impact demonstrated |
|---|---|---|
| **Time to a model-selection decision** | Ad hoc trial-and-error across notebooks or chat playgrounds, spread over days | A live, parallel, apples-to-apples comparison — latency, tokens, throughput — in under a minute |
| **Confidence in the choice, and bias awareness** | A single anecdotal impression, prone to whichever answer was read first | A blind, randomized-order judge scores both answers on a fixed rubric, and the tool refuses to let a model judge itself |
| **Safe exploration on shared AI spend** | Uncontrolled ad hoc testing against a shared, billable endpoint | Built-in guardrails — per-IP rate limits, concurrency caps, prompt/output token caps — keep experimentation from becoming a spending risk |

The KPI that carries the argument is **time to a defensible model-selection decision**:
it converts a debate that used to run on gut feel into one a platform lead can back with
numbers, in the time it takes to type a prompt.

### 1.4 Delivering the demo

#### Presenter verification (5 minutes before)

- [ ] The demo page opens at the address provided and the two model dropdowns populate
  automatically (click **Refresh** if either is empty)
- [ ] A test run (enter a prompt, pick two different models, run the comparison) streams
  back results with latency, TTFT and token counts for both
- [ ] The optional **⚖ judge** action returns a scored verdict

#### Demonstration sequence

1. *(0–1 min)* Open the page and point at the model dropdowns. *"These aren't a fixed
   list — they're read live from your team's own Foundry project. Deploy a new model
   and it shows up here."*
2. *(1–3 min)* Enter a prompt, select two different deployments, and run the comparison.
   Watch both stream back side by side. *"Same prompt, same instant, same measurement —
   this is as fair a comparison as you can get."* Call out latency, time-to-first-token
   and tokens/sec as they land.
3. *(3–4 min)* Point out that a reasoning model's controls (temperature, top-p) grey out
   automatically. *"The tool adapts to what each model actually supports instead of
   sending a request it knows will fail."*
4. *(4–5 min)* Click **⚖ judge**. Show the 1–5 scores across four criteria and the
   declared winner. *"This judge never sees which model produced which answer, and it's
   never one of the two being judged."*
5. Close by exporting the run to CSV/JSON. *"Enough of a record to defend the decision
   in a review, not just a screenshot."*

#### Key moments

- **Live, not curated** — the model list is your team's actual deployments, discovered
  at runtime.
- **Fair, parallel measurement** — identical prompt, identical instant, symmetric
  metrics.
- **A judge designed against its own bias** — blind, randomized order, and it can never
  judge itself.

### 1.5 Anticipated questions

**"Is this a benchmark I can trust?"** — It's an interactive, single-shot comparison,
not a statistical evaluation. For repeatable, dataset-scale scoring, point to the
[Azure AI Evaluation SDK](https://learn.microsoft.com/azure/ai-foundry/how-to/develop/evaluate-sdk).
For latency specifically, a few repeated runs read by median are far more meaningful
than one number.

**"Can the judge favor its own model family?"** — The tool guarantees the judge is never
one of the two candidates, and it reports when the judge shares a model family with
either candidate rather than hiding the risk. That transparency is the mitigation, not a
claim of zero bias.

**"Is our data used to train the models?"** — No. Azure OpenAI Service does not use
customer prompts or completions to train the underlying models, and this tool does not
log raw prompts or responses to observability.

**"What does it cost to run?"** — Standard consumption-priced token billing for two
short chat completions per run, plus a third if the judge is invoked. Per-model dollar
pricing isn't exposed by the deployment API, which is why the tool compares tokens
rather than a computed cost.

**"Is it safe to expose this broadly?"** — It runs on a shared managed identity behind
several guardrails — per-IP rate limiting, a global concurrency cap, prompt/output token
caps, per-model timeouts and a discovery refresh debounce — specifically because a
public comparison tool on a shared identity is a potential spending proxy otherwise.

**"How long would it take to standardize on a model?"** — A short structured pass —
running the shortlist against a handful of real workload prompts, a few repetitions
each — is typically a few days of effort; §1.6 is where that shortlist gets defined.

### 1.6 From demo to next step

Propose a **structured model-shortlist evaluation**: pick 2–4 candidate deployments and
a handful of prompts representative of a real workload, run each pairing a few times to
smooth out cold-path variance, and use the results — plus the Azure AI Evaluation SDK
for anything that needs dataset-scale rigor — to set the default model for that
workload class.

### 1.7 What this demo is not

The comparison is a single interactive run, not a statistical benchmark — results
reflect whatever is deployed in the connected Foundry project at the time, and will
differ across environments and over time as deployments change. Cost in dollars is
never shown. The blind judge produces one anecdotal verdict, not a validated evaluation
metric.

### Glossary

- **TTFT (time to first token)** — how long after sending a request the first piece of
  generated text arrives; a proxy for perceived responsiveness.
- **Throughput** — completion tokens generated per second, once generation has started.
- **LLM-as-judge** — using a model to score or compare other models' outputs against a
  rubric, instead of (or alongside) a human reviewer.
- **Reasoning model** — a model family (e.g. `gpt-5.x`, `o1`/`o3`) that spends hidden
  "thinking" tokens and does not accept `temperature`/`top_p`.
- **Managed identity** — an Azure AD identity assigned to the app itself, used here to
  call Foundry/Azure OpenAI without a stored secret.
- **Foundry deployment** — a named, callable instance of a model inside an Azure AI
  Foundry project.

> *To prepare the environment for this demo, share Part 2 with your technical contact.*

---

## Part 2 · Technical Brief

### 2.1 Technical profile

| | |
|---|---|
| **Status** | Experimental |
| **Orchestration** | Parallel fan-out inference + an optional, explicit LLM-as-judge step |
| **Models** | Dynamic — whichever chat-capable deployments exist in the connected Foundry project; the judge model is auto-selected (or pinned via `JUDGE_MODEL`) |
| **Azure services** | Azure AI Foundry (discovery) · Azure OpenAI (inference) |
| **Stack** | FastAPI · vanilla HTML/JS · Terraform (unified deploy only) |
| **Author** | @heblasco |

### 2.2 The architecture

```
Browser ── GET /api/models?refresh= ──► discovery.get_models()  (cached ~60s)
                                          ├─ AIProjectClient.deployments.list()  (project, primary)
                                          ├─ ARM CognitiveServicesManagementClient  (fallback)
                                          └─ static EVALUATOR_MODELS list        (last resort)

Browser ── POST /api/compare {prompt, models:[A,B], params} ──► SSE stream
                                          └─ inference.compare()  — asyncio.gather, truly parallel
                                                ├─ candidate-model-a  (AsyncAzureOpenAI, streamed)
                                                └─ candidate-model-b  (AsyncAzureOpenAI, streamed)
                                          per model: TTFT / total latency / tokens / throughput
                                          measured from the same clock, MI token prefetched first

Browser ── POST /api/judge {prompt, a, b} ──► judge.judge()
                                          ├─ pick_judge_model() — strongest OTHER selectable
                                          │  deployment; refuses to return either candidate
                                          └─ blind, randomized A/B order → 1–5 × 4 criteria → winner
```

#### Components

| Component | Where | Role |
|---|---|---|
| Backend + SSE | [app/backend/main.py](app/backend/main.py) | FastAPI single container; serves the UI at `/` and the JSON/SSE API |
| Discovery | [app/backend/discovery.py](app/backend/discovery.py) | Live model discovery with graceful degradation (project → ARM → static), 60s cache |
| Inference | [app/backend/inference.py](app/backend/inference.py) | Parallel streamed Chat Completions calls; fair TTFT/latency/tokens/throughput measurement; per-model capability filtering |
| Judge | [app/backend/judge.py](app/backend/judge.py) | Blind, randomized-order, non-self LLM-as-judge with structured JSON output |
| Guardrails | [app/backend/guardrails.py](app/backend/guardrails.py) | Per-IP rate limit, global concurrency semaphore, SSE stream cap, refresh debounce |
| Azure clients | [app/backend/azure_clients.py](app/backend/azure_clients.py) | Shared managed-identity credential + `AsyncAzureOpenAI` client; token prefetch so auth doesn't skew the first model's timing |
| Frontend | [app/frontend/](app/frontend/) | Vanilla HTML/JS UI |
| Infra | root [infra/](../../infra/) | Terraform; joins the shared AgentVerse Foundry project (unified deploy only — no standalone `infra/` in this folder) |

#### The agents

| Agent | Kind | Model | Job |
|---|---|---|---|
| `candidate-model-a` | Model call | Dynamic (user-selected) | Streams the prompt to the first selected Foundry deployment; reports latency, TTFT and token usage |
| `candidate-model-b` | Model call | Dynamic (user-selected) | Streams the same prompt to the second selected deployment, in parallel |
| `blind-judge` | LLM agent (explicit action) | Dynamic (auto-selected; never a candidate) | Blindly scores both answers 1–5 on four criteria with randomized A/B order and returns a winner |

### 2.3 Agentic patterns

| Pattern | Where in this demo | Why it matters here | In business terms |
|---|---|---|---|
| **Fan-out parallel inference** | `inference.compare()`, [app/backend/inference.py](app/backend/inference.py) | Both models run truly concurrently on identical input, from the same clock, for a fair comparison | Two experts answer the same question at the same moment |
| **Blind, randomized LLM-as-judge** | [app/backend/judge.py](app/backend/judge.py) | Candidate identity is hidden and A/B order is shuffled per run to reduce position bias | A blind taste test, not a rigged one |
| **Non-self-judging model selection** | `pick_judge_model()`, [app/backend/judge.py](app/backend/judge.py) | The judge is always the strongest deployment distinct from both candidates; family overlap is reported, not hidden | The referee never plays in the game — and says so if it's a close relative |
| **Capability-aware parameter filtering** | `build_params()`, [app/backend/inference.py](app/backend/inference.py) | Reasoning models reject `temperature`/`top_p` and need `max_completion_tokens`; the app sends only the valid intersection instead of erroring | The form adjusts itself to the model you picked |
| **Guardrailed shared-identity endpoint** | [app/backend/guardrails.py](app/backend/guardrails.py) | Rate limits, a concurrency cap and token caps protect a shared managed identity sitting behind a public endpoint | Guest access with a spending limit |

### 2.4 Technical setup

Run before a session; the end state is what §1.4's presenter verification checks.

- [ ] `az login` with a role on the shared Foundry account: **Azure AI Developer**
  (discovery) and **Cognitive Services OpenAI User** (inference)
- [ ] `cd src/model-evaluator && pip install -r requirements.txt`
- [ ] Set `PROJECT_ENDPOINT` (drives discovery) and `AZURE_OPENAI_ENDPOINT` (drives
  inference) — via `.env` or shell env
- [ ] Run: `uvicorn app.backend.main:app --port 8770` → http://localhost:8770
- [ ] Confirm `/healthz` reports `inference: true`, and the model dropdowns populate on
  load

### 2.5 Additional resources

#### Configuration

All via environment (injected by `infra/locals.tf` `computed_env` in the unified
deploy; no secrets baked in):

| Var | Purpose |
|---|---|
| `PROJECT_ENDPOINT` | Foundry project endpoint — drives model **discovery**. |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint — drives **inference**. |
| `AZURE_CLIENT_ID` | UAMI client id for `DefaultAzureCredential` in the container. |
| `OPENAI_API_VERSION` | Data-plane API version (default `2024-10-21`). |
| `JUDGE_MODEL` | Judge deployment override. If unset, unavailable, or one of the two candidates, the app picks the **strongest** other discovered chat model — it never self-judges. |
| `EVALUATOR_MODELS` | Optional comma-separated static fallback list (if discovery is unavailable). |
| `MAX_OUTPUT_TOKENS`, `MAX_PROMPT_CHARS`, `MAX_MODELS_PER_RUN`, `GLOBAL_CONCURRENCY`, `MAX_SSE_STREAMS`, `RATE_LIMIT_*`, `INFERENCE_TIMEOUT_SECONDS`, `DISCOVERY_CACHE_SECONDS` | Guardrail tuning (sensible defaults). |

Optional ARM fallback discovery (needs a management-plane read role, off by default):
`AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`, `AZURE_AI_ACCOUNT_NAME`.

#### API surface

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/models?refresh=1` | Discovered deployments + limits |
| POST | `/api/compare` | SSE stream of per-model results (parallel) |
| POST | `/api/judge` | Blind judge verdict for two answers |
| GET | `/healthz` | Liveness + config flags |

#### Deployment

Unified (AgentVerse portal) only — this demo has no standalone `infra/` of its own. It
joins the platform via [agentverse.yaml](agentverse.yaml) and the root
`infra/demos.auto.tfvars`, sharing the platform's Foundry project; `PROJECT_ENDPOINT`
and `AZURE_OPENAI_ENDPOINT` are injected automatically and no agents need registering
(there are no persistent agents here). See
[docs/adding-a-demo.md](../../docs/adding-a-demo.md).

#### Observability

Set `APPLICATIONINSIGHTS_CONNECTION_STRING` (injected by the unified deploy) to enable
Azure Monitor tracing (FastAPI + httpx instrumentation). Raw prompts and responses are
**not** logged.

#### Notes & limits

- **Interactive comparison, not an eval.** A single blind judgement is subject to
  positional and model-family bias. For repeatable, dataset-scale scoring
  (groundedness, similarity, etc.) use the
  [Azure AI Evaluation SDK](https://learn.microsoft.com/azure/ai-foundry/how-to/develop/evaluate-sdk).
- Cost is intentionally **not** shown (per-model pricing isn't exposed by the deployment
  API); compare tokens instead.
- For statistically meaningful latency, run a few repetitions and read the median — a
  one-shot number includes cold-path variance.
