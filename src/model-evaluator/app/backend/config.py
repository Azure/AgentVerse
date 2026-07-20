"""Model Evaluator — configuration (all from env; no secrets baked in).

The demo runs on the shared AgentVerse Foundry account. Endpoints and the
managed-identity client id are injected by infra/locals.tf computed_env; local
runs fall back to a .env / az-login DefaultAzureCredential.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "").strip() or default)
    except ValueError:
        return default


# --- Foundry / Azure OpenAI endpoints --------------------------------------
# Project endpoint (…/api/projects/<project>) drives dynamic model discovery.
PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT", "").strip()
# Azure OpenAI endpoint (https://<account>.openai.azure.com) drives inference.
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
# Chat Completions data-plane API version (pinned; see backend probe).
OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION", "2024-10-21").strip()
# AAD scope for data-plane inference + the deployments token.
COGNITIVE_SCOPE = "https://cognitiveservices.azure.com/.default"

# Managed-identity client id (UAMI) for DefaultAzureCredential in the container.
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "").strip()

# --- ARM fallback discovery (optional) -------------------------------------
AZURE_SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID", "").strip()
AZURE_RESOURCE_GROUP = os.getenv("AZURE_RESOURCE_GROUP", "").strip()
AZURE_AI_ACCOUNT_NAME = os.getenv("AZURE_AI_ACCOUNT_NAME", "").strip()

# --- Static fallback model list (comma-separated deployment names) ----------
STATIC_MODELS = [m.strip() for m in os.getenv("EVALUATOR_MODELS", "").split(",") if m.strip()]

# --- Observability ----------------------------------------------------------
APPLICATIONINSIGHTS_CONNECTION_STRING = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "").strip()
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "model-evaluator").strip()

# --- Guardrails (shared public endpoint on a shared identity) --------------
DISCOVERY_CACHE_SECONDS = _int("DISCOVERY_CACHE_SECONDS", 60)
DISCOVERY_TIMEOUT_SECONDS = _int("DISCOVERY_TIMEOUT_SECONDS", 15)
INFERENCE_TIMEOUT_SECONDS = _int("INFERENCE_TIMEOUT_SECONDS", 90)
MAX_OUTPUT_TOKENS = _int("MAX_OUTPUT_TOKENS", 1024)          # server clamp
MAX_PROMPT_CHARS = _int("MAX_PROMPT_CHARS", 16000)          # coarse guard
MAX_PROMPT_TOKENS = _int("MAX_PROMPT_TOKENS", 6000)          # token guard
MAX_MODELS_PER_RUN = _int("MAX_MODELS_PER_RUN", 2)          # v1 is A/B
GLOBAL_CONCURRENCY = _int("GLOBAL_CONCURRENCY", 8)           # in-flight model calls
MAX_SSE_STREAMS = _int("MAX_SSE_STREAMS", 6)
RATE_LIMIT_WINDOW_SECONDS = _int("RATE_LIMIT_WINDOW_SECONDS", 60)
RATE_LIMIT_MAX_REQUESTS = _int("RATE_LIMIT_MAX_REQUESTS", 20)  # per IP per window
REFRESH_MIN_INTERVAL_SECONDS = _int("REFRESH_MIN_INTERVAL_SECONDS", 15)

# Optional judge model override (else the app picks the strongest chat model
# distinct from the two candidates at request time). Pinned to a capable model
# via infra/locals.tf in the unified deploy; left empty for local runs.
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "").strip()
# Output budget for the judge. Reasoning judges (gpt-5.x/o*) spend hidden
# reasoning tokens against this budget, so keep it generous to avoid truncating
# the JSON verdict; non-reasoning judges use the smaller cap.
JUDGE_MAX_TOKENS = _int("JUDGE_MAX_TOKENS", 4000)
JUDGE_MAX_TOKENS_NONREASONING = _int("JUDGE_MAX_TOKENS_NONREASONING", 800)


def has_inference() -> bool:
    return bool(AZURE_OPENAI_ENDPOINT)
