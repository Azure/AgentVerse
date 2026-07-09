"""One gateway for all model access: Azure AI Foundry Agents, with replay mode.

Every agent calls `run_agent(...)` and nothing else. Two modes, chosen once:

- **Live** — `PROJECT_ENDPOINT` is set: get-or-create a persistent Foundry agent
  from the folder's `agent.yaml` + `instructions.md` (idempotent — reruns update
  instructions instead of duplicating), then thread -> message -> run -> parse
  the structured JSON reply. Auth is DefaultAzureCredential (managed identity in
  Azure, `az login` locally). One thread per disruption, inspectable in the
  Foundry portal.

- **Replay** — no `PROJECT_ENDPOINT` (or `REPLAY_MODE=true`): responses come from
  recorded fixtures in `agents/fixtures/<agent-name>/<fixture_key>.json`. The
  demo runs with zero Azure dependencies; callers can't tell the difference.

Fixtures are recorded from live runs via `scripts/run_demo.py --record` (or
hand-authored until the first live run).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

AGENTS_DIR = Path(__file__).resolve().parent.parent
FIXTURES_DIR = AGENTS_DIR / "fixtures"


class AgentRunError(RuntimeError):
    pass


def replay_mode() -> bool:
    if os.getenv("REPLAY_MODE", "").lower() in ("1", "true", "yes"):
        return True
    return not os.getenv("PROJECT_ENDPOINT")


def load_agent_spec(agent_dir: Path) -> dict:
    spec = yaml.safe_load((agent_dir / "agent.yaml").read_text(encoding="utf-8"))
    spec["instructions_text"] = (agent_dir / spec["instructions"]).read_text(encoding="utf-8")
    return spec


def run_agent(agent_dir: Path, payload: BaseModel, output_model: type[T], fixture_key: str) -> T:
    """Run one agent once and return its validated, typed output."""
    if replay_mode():
        return _run_replay(agent_dir.name, output_model, fixture_key)
    return _run_live(agent_dir, payload, output_model, fixture_key)


# ---- replay -------------------------------------------------------------------

def _run_replay(agent_name: str, output_model: type[T], fixture_key: str) -> T:
    fixture = FIXTURES_DIR / agent_name / f"{fixture_key}.json"
    if not fixture.exists():
        raise AgentRunError(
            f"Replay mode: no fixture for agent '{agent_name}', key '{fixture_key}'. "
            f"Expected {fixture}. Set PROJECT_ENDPOINT for a live run, or record "
            f"fixtures with scripts/run_demo.py --record."
        )
    return output_model.model_validate_json(fixture.read_text(encoding="utf-8"))


def record_fixture(agent_name: str, fixture_key: str, output: BaseModel) -> Path:
    """Persist a live response as the replay fixture for (agent, key)."""
    path = FIXTURES_DIR / agent_name / f"{fixture_key}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(output.model_dump_json(indent=2), encoding="utf-8")
    return path


# ---- live (Azure AI Foundry Agent Service) --------------------------------------
# NOTE: exercised only when PROJECT_ENDPOINT is configured; replay is the default
# and the path covered by evals. Verify against your azure-ai-projects version on
# the first live run.

_agent_id_cache: dict[str, str] = {}
_client = None


def _project_client():
    global _client
    if _client is None:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential

        _client = AIProjectClient(
            endpoint=os.environ["PROJECT_ENDPOINT"],
            credential=DefaultAzureCredential(),
        )
    return _client


def _get_or_create_agent(agent_dir: Path) -> str:
    """Idempotent: find the Foundry agent by name and sync its instructions, or
    create it. Returns the agent id."""
    spec = load_agent_spec(agent_dir)
    name = spec["name"]
    if name in _agent_id_cache:
        return _agent_id_cache[name]

    agents = _project_client().agents
    # agent.yaml may name the env var holding its deployment (model_env), so
    # different agents can use different deployments (chat vs. reasoning).
    model = os.getenv(spec.get("model_env", "MODEL_DEPLOYMENT_NAME"), "") or spec["model"]
    existing = next((a for a in agents.list_agents() if a.name == name), None)
    if existing is not None:
        agent = agents.update_agent(existing.id, model=model, instructions=spec["instructions_text"])
    else:
        agent = agents.create_agent(model=model, name=name, instructions=spec["instructions_text"])
    _agent_id_cache[name] = agent.id
    return agent.id


def _run_live(agent_dir: Path, payload: BaseModel, output_model: type[T], fixture_key: str) -> T:
    agents = _project_client().agents
    agent_id = _get_or_create_agent(agent_dir)

    thread = agents.threads.create()
    agents.messages.create(thread_id=thread.id, role="user", content=payload.model_dump_json())
    run = agents.runs.create_and_process(thread_id=thread.id, agent_id=agent_id)
    if run.status != "completed":
        raise AgentRunError(f"Agent '{agent_dir.name}' run ended '{run.status}': {run.last_error}")

    for message in agents.messages.list(thread_id=thread.id, order="descending"):
        if message.role == "assistant":
            text = "".join(p.text.value for p in message.content if hasattr(p, "text"))
            output = output_model.model_validate_json(_extract_json(text))
            # RECORD_FIXTURES=true: persist live responses as replay fixtures.
            if os.getenv("RECORD_FIXTURES", "").lower() in ("1", "true", "yes"):
                record_fixture(agent_dir.name, fixture_key, output)
            return output
    raise AgentRunError(f"Agent '{agent_dir.name}' returned no assistant message.")


def _extract_json(text: str) -> str:
    """Tolerate a ```json fenced block or surrounding prose around the JSON body."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    raise AgentRunError(f"No JSON object found in agent reply: {text[:200]!r}")
