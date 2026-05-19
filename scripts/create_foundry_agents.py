"""Create or version AgentVerse prompt agents in the existing Foundry project."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import AzureCliCredential

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentverse.foundry_definitions import AGENT_INSTRUCTIONS, MODEL_DEPLOYMENT_NAME, PROJECT_ENDPOINT


OUTPUT_PATH = Path(__file__).resolve().parent.parent / ".foundry" / "created-agents.json"


def main() -> None:
    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT", PROJECT_ENDPOINT)
    model = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", MODEL_DEPLOYMENT_NAME)
    client = AIProjectClient(endpoint=endpoint, credential=AzureCliCredential())
    created = []
    for agent_name, instructions in AGENT_INSTRUCTIONS.items():
        definition = PromptAgentDefinition(model=model, instructions=instructions)
        agent = client.agents.create_version(agent_name=agent_name, definition=definition)
        created.append(
            {
                "name": agent.name,
                "id": agent.id,
                "version": getattr(agent, "version", None),
                "model": model,
                "projectEndpoint": endpoint,
            }
        )
        print(f"{agent.name}: {agent.id} version={getattr(agent, 'version', None)}")
    OUTPUT_PATH.write_text(json.dumps(created, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
