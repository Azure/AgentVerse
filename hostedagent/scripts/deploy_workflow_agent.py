"""Create or version the AgentVerse hosted workflow agent in Foundry."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import HostedAgentDefinition, ProtocolVersionRecord
from azure.identity import AzureCliCredential

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
HOSTED_ROOT = ROOT / "hostedagent"
STATE_DIR = HOSTED_ROOT / ".foundry"
IMAGE_PATH = STATE_DIR / "workflow-image.json"
OUTPUT_PATH = STATE_DIR / "workflow-agent.json"

from agentverse.foundry_definitions import MODEL_DEPLOYMENT_NAME, PROJECT_ENDPOINT


def main() -> None:
    image_info = json.loads(IMAGE_PATH.read_text(encoding="utf-8"))
    image = os.environ.get("AGENTVERSE_WORKFLOW_IMAGE", image_info["image"])
    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT", PROJECT_ENDPOINT)
    model = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", MODEL_DEPLOYMENT_NAME)
    agent_name = os.environ.get("AGENTVERSE_WORKFLOW_AGENT_NAME", "AgentVerseWorkflowAgent")
    definition = HostedAgentDefinition(
        image=image,
        cpu=os.environ.get("AGENTVERSE_WORKFLOW_CPU", "1"),
        memory=os.environ.get("AGENTVERSE_WORKFLOW_MEMORY", "2Gi"),
        container_protocol_versions=[ProtocolVersionRecord(protocol="responses", version="1.0.0")],
        environment_variables={
            "AZURE_AI_PROJECT_ENDPOINT": endpoint,
            "AZURE_AI_MODEL_DEPLOYMENT_NAME": model,
            "CONTENT_UNDERSTANDING_ENDPOINT": os.environ.get(
                "CONTENT_UNDERSTANDING_ENDPOINT",
                "https://agent-verse-resource.cognitiveservices.azure.com/",
            ),
            "AGENTVERSE_USE_DEFAULT_AZURE_CREDENTIAL": "1",
        },
    )
    client = AIProjectClient(endpoint=endpoint, credential=AzureCliCredential())
    agent = client.agents.create_version(
        agent_name=agent_name,
        definition=definition,
        headers={"Foundry-Features": "HostedAgents=V1Preview"},
    )
    payload = {
        "name": agent.name,
        "id": agent.id,
        "version": getattr(agent, "version", None),
        "image": image,
        "projectEndpoint": endpoint,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
