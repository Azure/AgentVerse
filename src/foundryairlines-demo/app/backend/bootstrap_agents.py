"""Bootstrap persistent Foundry **prompt agents** for the demo.

Creates two prompt agents server-side using `PromptAgentDefinition`:

  1. ``flights-agent`` — formats the lowest-occupancy flights as JSON
  2. ``events-agent``  — proposes one **real** upcoming event per flight,
                        powered by the **Bing Grounding** tool (persistent,
                        attached to the agent so it shows up under
                        "Agents → Tools" in the Foundry portal)

Both agents persist in the project: open them in the Foundry portal at
https://ai.azure.com → your project → Agents — and you can chat with them
manually for testing.

Environment (read from ``app/.env``):

  PROJECT_ENDPOINT          Required. Foundry project endpoint.
  MODEL_DEPLOYMENT_NAME     Default: gpt-4.1
  BING_CONNECTION_NAME      Default: bing-grounding
  FLIGHTS_AGENT_NAME        Default: flights-agent
  EVENTS_AGENT_NAME         Default: events-agent

Run:

  python -m app.backend.bootstrap_agents          # idempotent upsert
  python -m app.backend.bootstrap_agents --reset  # delete + recreate

Doc references:
  https://learn.microsoft.com/en-us/azure/foundry/agents/quickstarts/prompt-agent
  https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/bing-tools
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
load_dotenv(ROOT / ".env", override=True)

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
MODEL = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1")
BING_CONNECTION_NAME = os.getenv("BING_CONNECTION_NAME", "bing-grounding")
FLIGHTS_AGENT_NAME = os.getenv("FLIGHTS_AGENT_NAME", "flights-agent")
EVENTS_AGENT_NAME = os.getenv("EVENTS_AGENT_NAME", "events-agent")
CACHE_PATH = ROOT / "agents.json"


# ---------------------------------------------------------------------------
# Agent prompts (instructions). These are part of the public contract so users
# can replicate the agents standalone in the Foundry portal — the README
# quotes both verbatim.
# ---------------------------------------------------------------------------

FLIGHTS_INSTRUCTIONS = """\
You are a revenue analyst for an airline. The user message contains a JSON
array of raw flight rows from the internal flights database.

Return ONLY a JSON array (no prose, no code fences) preserving each row and
exposing exactly these fields per flight:

  - id                  (integer, original row id)
  - code                (flight code, e.g. "VY1234")
  - origin              (IATA code)
  - destination         (IATA code)
  - destination_city    (string)
  - destination_country (string)
  - date                (YYYY-MM-DD)
  - occupancy_pct       (one decimal)
  - price_eur           (integer euros)

Order the array by occupancy_pct ascending (lowest occupancy first)."""

EVENTS_INSTRUCTIONS = """\
You are a cultural concierge for an airline. The conversation history contains
a JSON array of flights with destination_city, destination_country and date.

For EACH flight, use the **Bing Grounding** tool to search the live web for
ONE real, public, upcoming event in that city around that date — for example
festivals, concerts, sports matches, exhibitions, conferences. Prefer events
that are well-documented and that a traveler could actually attend.

Return ONLY a JSON array (no prose, no code fences) with the same length and
ordering as the input flights. Each element must have:

  - flight_id         (integer matching the input)
  - title             (max 8 words, the event name)
  - short_description (max 14 words, what it is and when)
  - source_url        (the Bing search result URL you trusted)

If you cannot find a real event for a flight, set title to "Local highlights"
and short_description to a generic one-line cultural pitch for that city, and
set source_url to an empty string."""


def _load_cache() -> Dict[str, Any]:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cache(data: Dict[str, Any]) -> None:
    CACHE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _delete_legacy_assistants(cache: Dict[str, Any]) -> None:
    legacy_ids = [
        v for k, v in cache.items()
        if k.endswith("_id") and isinstance(v, str) and v.startswith("asst_")
    ]
    if not legacy_ids:
        return
    try:
        from azure.ai.agents import AgentsClient
        legacy = AgentsClient(
            endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential()
        )
        for aid in legacy_ids:
            try:
                legacy.delete_agent(aid)
                print(f"[bootstrap] deleted legacy assistant {aid}")
            except Exception as ex:
                print(f"[bootstrap] could not delete {aid}: {ex}")
    except Exception as ex:
        print(f"[bootstrap] legacy cleanup skipped: {ex}")


def _delete_prompt_agent(project: AIProjectClient, name: str) -> None:
    try:
        project.agents.delete_agent(agent_name=name)
        print(f"[bootstrap] deleted prompt agent {name}")
    except Exception as ex:
        print(
            f"[bootstrap] no prior prompt agent '{name}' (ok): "
            f"{ex.__class__.__name__}"
        )


def _resolve_bing_connection(project: AIProjectClient) -> str:
    """Return the project-scoped connection ID for the Bing Grounding resource.

    Raises a friendly error if the connection has not been created in the
    Foundry portal yet (this is the one piece of one-time manual setup).
    """
    try:
        conn = project.connections.get(BING_CONNECTION_NAME)
    except Exception as ex:
        raise RuntimeError(
            f"\n\n[bootstrap] No Foundry connection named "
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


def ensure_persistent_agents(reset: bool = False) -> Dict[str, str]:
    """Create or upsert the two prompt agents server-side. Idempotent."""
    cache = _load_cache()
    project = AIProjectClient(
        endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential()
    )

    _delete_legacy_assistants(cache)

    if reset:
        _delete_prompt_agent(project, FLIGHTS_AGENT_NAME)
        _delete_prompt_agent(project, EVENTS_AGENT_NAME)

    # ---- Agent #1: flights formatter (no tools) ----
    flights_agent = project.agents.create_version(
        agent_name=FLIGHTS_AGENT_NAME,
        definition=PromptAgentDefinition(
            model=MODEL,
            instructions=FLIGHTS_INSTRUCTIONS,
        ),
        description="Formats the lowest-occupancy flights as a strict JSON array.",
    )
    print(
        f"[bootstrap] flights agent: name={flights_agent.name} "
        f"version={flights_agent.version}"
    )

    # ---- Agent #2: events finder, with Bing Grounding tool attached ----
    bing_connection_id = _resolve_bing_connection(project)
    events_agent = project.agents.create_version(
        agent_name=EVENTS_AGENT_NAME,
        definition=PromptAgentDefinition(
            model=MODEL,
            instructions=EVENTS_INSTRUCTIONS,
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
        description="Finds one real public event per flight using Bing Grounding.",
    )
    print(
        f"[bootstrap] events agent:  name={events_agent.name} "
        f"version={events_agent.version}  bing_connection={BING_CONNECTION_NAME}"
    )

    out = {
        "flights_name": flights_agent.name,
        "events_name": events_agent.name,
        "flights_id": flights_agent.id,
        "events_id": events_agent.id,
        "agent_kind": "prompt-agent-v2",
        "bing_connection": BING_CONNECTION_NAME,
    }
    _save_cache(out)
    return out


if __name__ == "__main__":
    reset = "--reset" in sys.argv
    ids = ensure_persistent_agents(reset=reset)
    print(json.dumps(ids, indent=2))
