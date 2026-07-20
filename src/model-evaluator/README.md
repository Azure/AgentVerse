# Model Evaluator

Send **one prompt to two Azure AI Foundry model deployments in parallel** and
compare them side by side — latency, time-to-first-token, token usage,
throughput and (optionally) a blind LLM-judge verdict.

Part of the [AgentVerse](../../README.md) platform. Single container: FastAPI
serves the UI at `/` and the JSON/SSE API.

![tab](../../docs/assets/model-evaluator.png)

## What it does

- **Live model discovery** — the two dropdowns are populated from your shared
  Foundry project at runtime (`AIProjectClient.deployments.list()`). Deploy a new
  model and it appears on **Refresh**. Only chat-capable deployments are
  selectable; image/realtime/embedding models are listed but disabled.
- **Fair, parallel measurement** — each model gets **one streamed** Chat
  Completions request. The managed-identity token is prefetched before any timer
  starts; **TTFT** is the time to the first non-empty generated token; **total
  latency** covers the whole stream including the final usage frame; **throughput**
  = completion tokens ÷ generation time. Token counts come from the model's own
  `usage` report (`stream_options.include_usage`).
- **Capability-aware parameters** — reasoning models (`gpt-5.x`, `o*`) reject
  `temperature`/`top_p` and use `max_completion_tokens`; the UI disables the
  unsupported controls and the backend sends only the valid intersection.
- **Optional blind judge** — an explicit ⚖ action runs an LLM judge that scores
  both answers 1–5 on helpfulness/correctness/completeness/coherence with
  **randomized A/B order** (position-bias mitigation) and treats the candidate
  answers as untrusted data. Anecdotal, not statistical.
- **Export & history** — export a run to JSON/CSV; a browser-local history keeps
  your recent comparisons.

## Guardrails

This runs on a **public** endpoint over a **shared managed identity**, so it is a
potential spending proxy. Built-in mitigations: model names validated against the
discovered set, per-IP sliding-window rate limit, global concurrency semaphore,
prompt/output token caps, per-model timeout, SSE stream cap, and a discovery
refresh debounce. Raw prompts/responses are **not** logged to App Insights.

## Quick start

Local (uses your `az login` via `DefaultAzureCredential`):

```bash
cd src/model-evaluator
pip install -r requirements.txt

# point at the shared Foundry account
$env:PROJECT_ENDPOINT      = "https://<account>.services.ai.azure.com/api/projects/<project>"
$env:AZURE_OPENAI_ENDPOINT = "https://<account>.openai.azure.com"

uvicorn app.backend.main:app --port 8770
# open http://localhost:8770
```

Your identity needs **Azure AI Developer** (discovery) and **Cognitive Services
OpenAI User** (inference) on the shared account.

## Configuration

All via environment (injected by `infra/locals.tf` `computed_env` in the unified
deploy; no secrets baked in):

| Var | Purpose |
| --- | --- |
| `PROJECT_ENDPOINT` | Foundry project endpoint — drives model **discovery**. |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint — drives **inference**. |
| `AZURE_CLIENT_ID` | UAMI client id for `DefaultAzureCredential` in the container. |
| `OPENAI_API_VERSION` | Data-plane API version (default `2024-10-21`). |
| `JUDGE_MODEL` | Judge deployment (pinned to `gpt-5.6-sol` in the unified deploy). If unset — or if the pinned model is unavailable or is one of the two candidates — the app picks the **strongest** other discovered chat model; it never self-judges. |
| `EVALUATOR_MODELS` | Optional comma-separated static fallback list (if discovery is unavailable). |
| `MAX_OUTPUT_TOKENS`, `MAX_PROMPT_CHARS`, `MAX_MODELS_PER_RUN`, `GLOBAL_CONCURRENCY`, `MAX_SSE_STREAMS`, `RATE_LIMIT_*`, `INFERENCE_TIMEOUT_SECONDS`, `DISCOVERY_CACHE_SECONDS` | Guardrail tuning (sensible defaults). |

Optional ARM fallback discovery (needs a management-plane read role, off by
default): `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`, `AZURE_AI_ACCOUNT_NAME`.

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET`  | `/api/models?refresh=1` | Discovered deployments + limits. |
| `POST` | `/api/compare` | SSE stream of per-model results (parallel). |
| `POST` | `/api/judge` | Blind judge verdict for two answers. |
| `GET`  | `/healthz` | Liveness + config flags. |

## Notes & limits

- **Interactive comparison, not an eval.** A single blind judgement is
  subject to positional and model-family bias. For repeatable, dataset-scale
  scoring (groundedness, similarity, etc.) use the
  [Azure AI Evaluation SDK](https://learn.microsoft.com/azure/ai-foundry/how-to/develop/evaluate-sdk).
- Cost is intentionally **not** shown (per-model pricing isn't exposed by the
  deployment API); compare tokens instead.
- For statistically meaningful latency, run a few repetitions and read the median
  — one-shot numbers include cold-path variance.
