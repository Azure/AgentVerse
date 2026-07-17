"""Shared Azure credential + Azure OpenAI async client (managed identity).

One process-wide AsyncDefaultAzureCredential and one AsyncAzureOpenAI client are
reused so connection pools stay warm (fairer latency) and the MI token is minted
once. `prefetch_token()` warms the token cache before any per-model timer starts,
so the first model isn't penalised by the auth round-trip.
"""
from __future__ import annotations

import asyncio
import sys
from typing import Optional

# On Windows the default Proactor loop is incompatible with the aiohttp
# transport used by azure-identity's async credential; use the selector loop.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI

from . import config

_credential: Optional[DefaultAzureCredential] = None
_client: Optional[AsyncAzureOpenAI] = None
_lock = asyncio.Lock()


def _new_credential() -> DefaultAzureCredential:
    if config.AZURE_CLIENT_ID:
        return DefaultAzureCredential(managed_identity_client_id=config.AZURE_CLIENT_ID)
    return DefaultAzureCredential()


async def get_credential() -> DefaultAzureCredential:
    global _credential
    if _credential is None:
        async with _lock:
            if _credential is None:
                _credential = _new_credential()
    return _credential


async def get_openai_client() -> AsyncAzureOpenAI:
    """Lazily build the shared AsyncAzureOpenAI client (AAD token provider)."""
    global _client
    if _client is None:
        async with _lock:
            if _client is None:
                cred = await get_credential()
                token_provider = get_bearer_token_provider(cred, config.COGNITIVE_SCOPE)
                _client = AsyncAzureOpenAI(
                    azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
                    azure_ad_token_provider=token_provider,
                    api_version=config.OPENAI_API_VERSION,
                    max_retries=0,  # measure raw latency; we handle errors per model
                )
    return _client


async def prefetch_token() -> None:
    """Warm the MI token cache so it doesn't skew the first model's timing."""
    try:
        cred = await get_credential()
        await cred.get_token(config.COGNITIVE_SCOPE)
    except Exception:
        # Non-fatal: the per-model call will surface a real auth error.
        pass


async def aclose() -> None:
    global _client, _credential
    if _client is not None:
        await _client.close()
        _client = None
    if _credential is not None:
        await _credential.close()
        _credential = None
