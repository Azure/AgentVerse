"""Foundry hosted-agent client — routes claim processing to the deployed agent.

This is the *parity bridge* for the multi-brand demo. Both brands (white-label /
Helix and Santander) are the same app differentiated only by branding. The claims
pipeline itself is brand-agnostic, so when ``USE_FOUNDRY_AGENT=true`` BOTH brand
backends call the **same** Foundry hosted agent and therefore behave identically by
construction — branding stays entirely in the frontend (``dashboard/src/brand.ts``)
and the brand-only voice/intake prompts (``agents/shared/brand.py``).

It mirrors the ``process_claim`` contract exactly (same input dict, same decision
dict, same ``progress_callback(stage, status, data)`` streaming), so it is a drop-in
alternative to the in-process MAF/legacy orchestrator. ``agents/orchestrator/agent.py``
dispatches here when the flag is set and falls back to in-process on any error.

Environment:
    USE_FOUNDRY_AGENT        "true" to route through Foundry (default false).
    FOUNDRY_AGENT_ENDPOINT   Invocations URL of the deployed agent. Defaults to the
                             demo agent endpoint.
    FOUNDRY_AGENT_API_VERSION  REST api-version (default 2025-11-15-preview).
    FOUNDRY_TOKEN            Optional pre-fetched bearer token (else ManagedIdentity /
                             DefaultAzureCredential for https://ai.azure.com).
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_ENDPOINT = (
    "https://ai-account-kzrzuypevlok4.services.ai.azure.com/api/projects/"
    "ai-project-ins-ai-foundry/agents/insurance-claims-orchestrator/endpoint/protocols/invocations"
)
_API_VERSION = os.environ.get("FOUNDRY_AGENT_API_VERSION", "2025-11-15-preview")

_token: str | None = None
_token_expires_at: float = 0.0


def _get_token() -> str:
    global _token, _token_expires_at
    env_token = os.environ.get("FOUNDRY_TOKEN")
    if env_token:
        return env_token
    if _token and time.time() < _token_expires_at - 60:
        return _token
    from azure.identity import DefaultAzureCredential

    tok = DefaultAzureCredential().get_token("https://ai.azure.com/.default")
    _token = tok.token
    _token_expires_at = tok.expires_on
    return _token


def _endpoint() -> str:
    return os.environ.get("FOUNDRY_AGENT_ENDPOINT", _DEFAULT_ENDPOINT).rstrip("/")


def _session_id(claim_id: str) -> str:
    raw = f"{claim_id}-{uuid.uuid4().hex}".replace(" ", "")
    safe = "".join(c for c in raw if c.isalnum() or c in "-_")
    return safe[:128] if len(safe) >= 8 else f"sess-{uuid.uuid4().hex}"


async def process_claim_foundry(claim_input: dict, progress_callback=None) -> dict:
    """Invoke the deployed Foundry agent; mirrors ``process_claim`` exactly."""
    url = f"{_endpoint()}?api-version={_API_VERSION}&agent_session_id={_session_id(claim_input.get('claim_id', 'claim'))}"
    headers = {"Authorization": f"Bearer {_get_token()}", "Content-Type": "application/json"}

    # No callback → simple request/response (cheaper, no SSE).
    if progress_callback is None:
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(url, headers=headers, json={"claim": claim_input, "stream": False})
            resp.raise_for_status()
            return resp.json()

    # Callback → stream SSE and forward stage events, then return the final decision.
    result: dict | None = None
    event: str | None = None
    async with httpx.AsyncClient(timeout=300) as client:
        async with client.stream("POST", url, headers=headers, json={"claim": claim_input, "stream": True}) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                if line.startswith("event:"):
                    event = line[len("event:"):].strip()
                elif line.startswith("data:"):
                    payload = json.loads(line[len("data:"):].strip())
                    if event == "progress":
                        await progress_callback(payload.get("stage"), payload.get("status"), payload.get("data", {}))
                    elif event == "result":
                        result = payload
                    elif event == "error":
                        raise RuntimeError(payload.get("error", "Foundry agent error"))
    if result is None:
        raise RuntimeError("Foundry agent returned no result event")
    return result
