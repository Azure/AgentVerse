"""Shared Azure OpenAI client.

Two routing modes controlled by env var ``USE_APIM_GATEWAY``:

1. ``false`` (default): direct call to Azure OpenAI using a bearer token
   obtained via ``az account get-access-token``. Used for local dev when APIM
   is not yet provisioned.

2. ``true``: route through APIM AI Gateway (managed-identity auth, content
   safety, token-limits, telemetry). The agent only carries an APIM
   subscription key — secrets stay inside the gateway.

Required env vars:
- ``AZURE_OPENAI_ENDPOINT`` (always, even in APIM mode for legacy callers)
- ``USE_APIM_GATEWAY``      (optional, default ``false``)
- ``APIM_GATEWAY_URL``      (when APIM is on) — e.g. ``https://my-apim.azure-api.net``
- ``APIM_SUBSCRIPTION_KEY`` (when APIM is on) — Ocp-Apim-Subscription-Key header
- ``AGENT_ID``              (optional, default ``unknown``) — emitted as ``X-Agent-Id``
                            so APIM can rate-limit and meter per agent
"""

import os
import subprocess
import logging
import time
import httpx
from openai import AsyncAzureOpenAI

# Corp network MITMs TLS — for demo we skip verify (endpoint is private Azure).
_http_client = httpx.AsyncClient(verify=False)

logger = logging.getLogger(__name__)

_cached_token: str | None = None
_token_expires: float = 0
_client: AsyncAzureOpenAI | None = None


def _use_apim() -> bool:
    return os.environ.get("USE_APIM_GATEWAY", "false").lower() in ("1", "true", "yes")


def _get_token_via_default_credential() -> str | None:
    """Try azure-identity DefaultAzureCredential.

    Works in CI (federated OIDC via azure/login) and on dev boxes with az CLI.
    Returns None if azure-identity is not installed (fall back to az CLI).
    """
    try:
        from azure.identity import DefaultAzureCredential  # type: ignore
    except ImportError:
        return None
    try:
        cred = DefaultAzureCredential(
            exclude_interactive_browser_credential=True,
            process_timeout=60,
        )
        token = cred.get_token("https://cognitiveservices.azure.com/.default")
        logger.info("Got Azure token via DefaultAzureCredential")
        return token.token
    except Exception as e:  # noqa: BLE001
        logger.warning("DefaultAzureCredential failed: %s", e)
        return None


def _get_token_via_cli() -> str:
    """Get an Azure AD token by calling az CLI synchronously (local fallback)."""
    for az_path in [
        r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd",
        "az",
    ]:
        try:
            result = subprocess.run(
                [az_path, "account", "get-access-token",
                 "--resource", "https://cognitiveservices.azure.com",
                 "--query", "accessToken", "-o", "tsv"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                logger.info("Got Azure token via az CLI")
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    raise RuntimeError("Could not get Azure token. Run 'az login' first.")


def _get_token() -> str:
    """Get an Azure AD token preferring DefaultAzureCredential, falling back to az CLI."""
    token = _get_token_via_default_credential()
    if token:
        return token
    return _get_token_via_cli()


async def get_openai_client() -> AsyncAzureOpenAI:
    """Get a configured AsyncAzureOpenAI client.

    Uses APIM AI Gateway when ``USE_APIM_GATEWAY=true``, otherwise calls
    Azure OpenAI directly with a cached AAD token.
    """
    global _cached_token, _token_expires, _client

    if _use_apim():
        if _client is None:
            apim_url = os.environ.get("APIM_GATEWAY_URL", "").rstrip("/")
            apim_key = os.environ.get("APIM_SUBSCRIPTION_KEY", "")
            if not apim_url or not apim_key:
                raise RuntimeError(
                    "USE_APIM_GATEWAY=true requires APIM_GATEWAY_URL and "
                    "APIM_SUBSCRIPTION_KEY environment variables."
                )
            agent_id = os.environ.get("AGENT_ID", "unknown")
            apim_http = httpx.AsyncClient(
                verify=False,
                headers={
                    "Ocp-Apim-Subscription-Key": apim_key,
                    "X-Agent-Id": agent_id,
                },
            )
            _client = AsyncAzureOpenAI(
                azure_endpoint=apim_url,
                api_key="apim-managed",  # ignored; subscription key is in header
                api_version="2025-04-01-preview",
                http_client=apim_http,
            )
            logger.info("OpenAI client routed through APIM gateway (agent=%s)", agent_id)
        return _client

    if _cached_token is None or time.time() > _token_expires:
        _cached_token = _get_token()
        _token_expires = time.time() + 3000
        _client = None  # force new client with fresh token

    if _client is None:
        _client = AsyncAzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            azure_ad_token=_cached_token,
            api_version="2025-04-01-preview",
            http_client=_http_client,
        )

    return _client

