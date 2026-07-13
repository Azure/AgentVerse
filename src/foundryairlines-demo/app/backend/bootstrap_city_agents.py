"""Bootstrap persistent Foundry **prompt agent** for the city activities demo.

Creates one prompt agent server-side using `PromptAgentDefinition`:

  1. ``activities-agent`` — searches Bing for activities/attractions in a city,
                           powered by the **Bing Grounding** tool (persistent,
                           attached to the agent)

The agent persists in the project: open it in the Foundry portal at
https://ai.azure.com → your project → Agents.

Environment (read from ``app/.env``):

  PROJECT_ENDPOINT          Required. Foundry project endpoint.
  MODEL_DEPLOYMENT_NAME     Default: gpt-4.1
  BING_CONNECTION_NAME      Default: bing-grounding
  ACTIVITIES_AGENT_NAME     Default: activities-agent

Run:

  python -m app.backend.bootstrap_city_agents          # idempotent upsert
  python -m app.backend.bootstrap_city_agents --reset  # delete + recreate
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    BingGroundingSearchConfiguration,
    BingGroundingSearchToolParameters,
    BingGroundingTool,
    PromptAgentDefinition,
)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=False)

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
MODEL = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1")
BING_CONNECTION_NAME = os.getenv("BING_CONNECTION_NAME", "bing-grounding")
ACTIVITIES_AGENT_NAME = os.getenv("ACTIVITIES_AGENT_NAME", "activities-agent")
CACHE_PATH = ROOT / "city_agents.json"


# ---------------------------------------------------------------------------
# Agent prompt (instructions)
# ---------------------------------------------------------------------------

ACTIVITIES_INSTRUCTIONS = """\
You are a travel activities researcher. The user will provide a city name.

Use the **Bing Grounding** tool to search the live web for real activities,
attractions, festivals, events, restaurants, and experiences in that city that
a traveler should know about. Find 5 to 8 diverse items across categories like:
culture, food, nightlife, nature, sports, shopping, landmarks.

Return ONLY a JSON array (no prose, no code fences) with 5-8 elements.
Each element must have:

  - title             (max 6 words, the activity/place name)
  - description       (max 20 words, what it is and why it's worth visiting)
  - category          (one of: culture, food, nightlife, nature, sports, shopping, landmarks, events)
  - source_url        (the Bing search result URL you trusted)

Order the array by variety — do not cluster same categories together."""


def _load_cache() -> Dict[str, Any]:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cache(data: Dict[str, Any]) -> None:
    CACHE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _delete_prompt_agent(project: AIProjectClient, name: str) -> None:
    try:
        project.agents.delete_agent(agent_name=name)
        print(f"[bootstrap-city] deleted prompt agent {name}")
    except Exception as ex:
        print(
            f"[bootstrap-city] no prior prompt agent '{name}' (ok): "
            f"{ex.__class__.__name__}"
        )


def _resolve_bing_connection(project: AIProjectClient) -> str:
    """Return the project-scoped connection ID for the Bing Grounding resource."""
    try:
        conn = project.connections.get(BING_CONNECTION_NAME)
    except Exception as ex:
        raise RuntimeError(
            f"\n\n[bootstrap-city] No Foundry connection named "
            f"'{BING_CONNECTION_NAME}'.\n\n"
            f"Create it once in the Foundry portal:\n"
            f"  1. https://ai.azure.com → your project\n"
            f"  2. Management center → Connected resources → + Connection\n"
            f"  3. Choose 'Grounding with Bing Search'\n"
            f"  4. Pick your Bing resource and name the connection\n"
            f"     '{BING_CONNECTION_NAME}'\n"
            f"  5. Re-run this bootstrap.\n\n"
            f"Underlying error: {ex}"
        ) from ex
    return conn.id


def ensure_city_agents(reset: bool = False) -> Dict[str, str]:
    """Create or upsert the activities prompt agent server-side. Idempotent."""
    cache = _load_cache()
    project = AIProjectClient(
        endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential()
    )

    if reset:
        _delete_prompt_agent(project, ACTIVITIES_AGENT_NAME)

    # ---- Activities agent with Bing Grounding tool attached ----
    bing_connection_id = _resolve_bing_connection(project)
    activities_agent = project.agents.create_version(
        agent_name=ACTIVITIES_AGENT_NAME,
        definition=PromptAgentDefinition(
            model=MODEL,
            instructions=ACTIVITIES_INSTRUCTIONS,
            tools=[
                BingGroundingTool(
                    bing_grounding=BingGroundingSearchToolParameters(
                        search_configurations=[
                            BingGroundingSearchConfiguration(
                                project_connection_id=bing_connection_id,
                            )
                        ]
                    )
                )
            ],
        ),
        description="Searches Bing for activities and attractions in a given city.",
    )
    print(
        f"[bootstrap-city] activities agent: name={activities_agent.name} "
        f"version={activities_agent.version}  bing_connection={BING_CONNECTION_NAME}"
    )

    out = {
        "activities_name": activities_agent.name,
        "activities_id": activities_agent.id,
        "agent_kind": "prompt-agent-v2",
        "bing_connection": BING_CONNECTION_NAME,
    }
    _save_cache(out)
    return out


if __name__ == "__main__":
    reset = "--reset" in sys.argv
    ids = ensure_city_agents(reset=reset)
    print(json.dumps(ids, indent=2))
