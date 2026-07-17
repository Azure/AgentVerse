"""Dynamic model discovery for the shared Foundry account.

Ordering (graceful degradation):
  1. azure-ai-projects  AIProjectClient.deployments.list()  — project data plane,
     exposes capabilities so we can select chat-capable models precisely.
  2. ARM  CognitiveServicesManagementClient.deployments.list() — account inventory
     (needs subscription/rg/account + a read role).
  3. Static EVALUATOR_MODELS env list — marked stale.

A newly deployed Foundry model appears automatically (cache TTL ~60s, or
?refresh=1). Selectable = chat-capable text model; image/realtime/embeddings are
returned but marked unsupported (disabled in the UI), never silently selectable.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

from . import config
from .azure_clients import get_credential

# --- capability heuristics --------------------------------------------------

_NON_CHAT_HINTS = ("image", "realtime", "embedding", "embed", "whisper",
                   "transcribe", "audio", "tts", "dall", "sora", "moderation")


def _is_reasoning(model_name: str) -> bool:
    """gpt-5.x / o1 / o3 / o4 style models: no temperature/top_p, and they use
    max_completion_tokens instead of max_tokens (verified against gpt-5.1)."""
    n = (model_name or "").lower()
    return n.startswith(("gpt-5", "o1", "o3", "o4"))


def _classify(name: str, model_name: str, capabilities: Dict[str, Any]) -> Tuple[bool, str]:
    """Return (chat_capable, reason). Uses explicit capabilities first, then a
    conservative name-based registry; unknowns are treated as NOT selectable."""
    caps = {str(k).lower(): str(v).lower() for k, v in (capabilities or {}).items()}
    if caps:
        if caps.get("chat_completion") == "true" or caps.get("completion") == "true":
            return True, "chat_completion"
        # Capabilities present but chat explicitly absent/false → not chat.
        return False, "no chat capability"
    # No capability metadata (e.g. ARM path): fall back to name heuristics.
    lname = (model_name or name or "").lower()
    if any(h in lname for h in _NON_CHAT_HINTS):
        return False, "non-chat model family"
    if lname.startswith(("gpt-", "o1", "o3", "o4", "phi", "llama", "mistral", "deepseek")):
        return True, "known chat family (name)"
    return False, "unknown capability"


def _entry(name: str, model_name: str, model_version: str, publisher: str,
           capabilities: Dict[str, Any], source: str) -> Dict[str, Any]:
    chat, reason = _classify(name, model_name, capabilities)
    reasoning = _is_reasoning(model_name or name)
    return {
        "name": name,                       # deployment name (used as `model`)
        "model": model_name or name,
        "version": model_version or "",
        "publisher": publisher or "",
        "selectable": chat,
        "reason": reason,
        "reasoning": reasoning,             # UI: disable temperature/top_p
        "token_param": "max_completion_tokens" if reasoning else "max_tokens",
        "source": source,
    }


# --- discovery backends -----------------------------------------------------

async def _from_project() -> Optional[List[Dict[str, Any]]]:
    if not config.PROJECT_ENDPOINT:
        return None
    cred = await get_credential()

    def _list() -> List[Dict[str, Any]]:
        from azure.ai.projects import AIProjectClient  # sync SDK
        # A separate sync credential keeps the async loop clean.
        from azure.identity import DefaultAzureCredential as SyncCred
        sync_cred = (SyncCred(managed_identity_client_id=config.AZURE_CLIENT_ID)
                     if config.AZURE_CLIENT_ID else SyncCred())
        out: List[Dict[str, Any]] = []
        with AIProjectClient(endpoint=config.PROJECT_ENDPOINT, credential=sync_cred) as pc:
            for d in pc.deployments.list():
                if getattr(d, "type", "") and d.type != "ModelDeployment":
                    continue
                out.append(_entry(
                    name=getattr(d, "name", ""),
                    model_name=getattr(d, "model_name", ""),
                    model_version=getattr(d, "model_version", ""),
                    publisher=getattr(d, "model_publisher", ""),
                    capabilities=getattr(d, "capabilities", {}) or {},
                    source="project",
                ))
        return out

    return await asyncio.wait_for(asyncio.to_thread(_list), config.DISCOVERY_TIMEOUT_SECONDS)


async def _from_arm() -> Optional[List[Dict[str, Any]]]:
    if not (config.AZURE_SUBSCRIPTION_ID and config.AZURE_RESOURCE_GROUP and config.AZURE_AI_ACCOUNT_NAME):
        return None

    def _list() -> List[Dict[str, Any]]:
        from azure.identity import DefaultAzureCredential as SyncCred
        from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
        sync_cred = (SyncCred(managed_identity_client_id=config.AZURE_CLIENT_ID)
                     if config.AZURE_CLIENT_ID else SyncCred())
        client = CognitiveServicesManagementClient(sync_cred, config.AZURE_SUBSCRIPTION_ID)
        out: List[Dict[str, Any]] = []
        for d in client.deployments.list(config.AZURE_RESOURCE_GROUP, config.AZURE_AI_ACCOUNT_NAME):
            model = getattr(getattr(d.properties, "model", None), "name", "") if d.properties else ""
            version = getattr(getattr(d.properties, "model", None), "version", "") if d.properties else ""
            out.append(_entry(
                name=d.name or "", model_name=model, model_version=version,
                publisher="OpenAI", capabilities={}, source="arm",
            ))
        return out

    return await asyncio.wait_for(asyncio.to_thread(_list), config.DISCOVERY_TIMEOUT_SECONDS)


def _from_static() -> List[Dict[str, Any]]:
    return [_entry(name=m, model_name=m, model_version="", publisher="",
                   capabilities={}, source="static") for m in config.STATIC_MODELS]


# --- public cached API ------------------------------------------------------

_cache: Dict[str, Any] = {"ts": 0.0, "models": [], "source": "none", "error": None}
_disc_lock = asyncio.Lock()


async def _discover() -> Dict[str, Any]:
    errors = []
    for backend, fn in (("project", _from_project), ("arm", _from_arm)):
        try:
            models = await fn()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{backend}: {type(exc).__name__}: {exc}")
            continue
        if models:
            return {"models": models, "source": backend, "error": "; ".join(errors) or None}
    static = _from_static()
    return {"models": static, "source": "static" if static else "none",
            "error": "; ".join(errors) or None}


async def get_models(refresh: bool = False) -> Dict[str, Any]:
    now = time.monotonic()
    fresh = (now - _cache["ts"]) < config.DISCOVERY_CACHE_SECONDS
    if _cache["models"] and fresh and not refresh:
        return _snapshot()
    async with _disc_lock:
        now = time.monotonic()
        fresh = (now - _cache["ts"]) < config.DISCOVERY_CACHE_SECONDS
        if _cache["models"] and fresh and not refresh:
            return _snapshot()
        result = await _discover()
        # Keep the last good list if discovery came back empty.
        if result["models"] or not _cache["models"]:
            _cache["models"] = result["models"]
            _cache["source"] = result["source"]
        _cache["error"] = result["error"]
        _cache["ts"] = time.monotonic()
        return _snapshot()


def _snapshot() -> Dict[str, Any]:
    models = sorted(_cache["models"], key=lambda m: (not m["selectable"], m["name"]))
    return {
        "models": models,
        "source": _cache["source"],
        "error": _cache["error"],
        "fetched_at": _cache["ts"],
        "selectable_count": sum(1 for m in models if m["selectable"]),
    }


def find(name: str) -> Optional[Dict[str, Any]]:
    for m in _cache["models"]:
        if m["name"] == name:
            return m
    return None
