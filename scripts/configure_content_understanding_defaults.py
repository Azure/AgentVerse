"""Configure Content Understanding default model deployments for AgentVerse."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from azure.identity import AzureCliCredential

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentverse.content_understanding import DEFAULT_CONTENT_UNDERSTANDING_ENDPOINT, CONTENT_UNDERSTANDING_API_VERSION


def main() -> None:
    endpoint = (os.environ.get("CONTENT_UNDERSTANDING_ENDPOINT") or DEFAULT_CONTENT_UNDERSTANDING_ENDPOINT).rstrip("/")
    completion = os.environ.get("CONTENT_UNDERSTANDING_COMPLETION_DEPLOYMENT", "gpt-4.1-mini")
    embedding = os.environ.get("CONTENT_UNDERSTANDING_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
    body = json.dumps({"modelDeployments": {"gpt-4.1-mini": completion, "text-embedding-3-large": embedding}}).encode("utf-8")
    token = AzureCliCredential().get_token("https://cognitiveservices.azure.com/.default").token
    request = urllib.request.Request(
        f"{endpoint}/contentunderstanding/defaults?api-version={CONTENT_UNDERSTANDING_API_VERSION}",
        method="PATCH",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            print(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(exc.read().decode("utf-8", errors="replace")) from exc


if __name__ == "__main__":
    main()
