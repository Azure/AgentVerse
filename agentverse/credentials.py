"""Credential helpers shared by local and hosted AgentVerse flows."""

from __future__ import annotations

import os
import threading
import time

from azure.core.credentials import AccessToken, TokenCredential
from azure.identity import AzureCliCredential, DefaultAzureCredential


class CachedTokenCredential:
    """Cache Azure access tokens to avoid repeated Azure CLI subprocess calls."""

    def __init__(self, credential: TokenCredential, refresh_margin_seconds: int = 300) -> None:
        self._credential = credential
        self._refresh_margin_seconds = refresh_margin_seconds
        self._tokens: dict[tuple[str, ...], AccessToken] = {}
        self._lock = threading.Lock()

    def get_token(self, *scopes: str, **kwargs: object) -> AccessToken:
        key = tuple(scopes)
        now = int(time.time())
        with self._lock:
            cached = self._tokens.get(key)
            if cached and cached.expires_on - self._refresh_margin_seconds > now:
                return cached
            token = self._credential.get_token(*scopes, **kwargs)
            self._tokens[key] = token
            return token


def default_agentverse_credential() -> TokenCredential:
    """Return the credential strategy for the current AgentVerse runtime."""
    if os.environ.get("AGENTVERSE_USE_DEFAULT_AZURE_CREDENTIAL") == "1":
        return DefaultAzureCredential()

    timeout = int(os.environ.get("AGENTVERSE_AZURE_CLI_PROCESS_TIMEOUT_SECONDS", "60"))
    return CachedTokenCredential(AzureCliCredential(process_timeout=timeout))
