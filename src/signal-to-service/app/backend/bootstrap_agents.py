"""Bootstrap the three persistent Foundry **prompt agents** for Signal-to-Service.

Creates (idempotent upsert), server-side, using ``PromptAgentDefinition``:

  1. signal-to-service-diagnosis-agent — classifies the failure mode + RUL from telemetry
  2. signal-to-service-knowledge-agent — summarises & cites the SOP passages we retrieve
  3. signal-to-service-action-agent    — drafts the technician work-order summary

None of them use hosted tools: retrieval (RAG) and the CMMS/scheduler actions run
in the app's own code, so the agents stay deterministic and the demo runs locally.

Environment (read from app/.env, but shell/injected env wins):

  PROJECT_ENDPOINT           Required. Foundry project endpoint.
  MODEL_DEPLOYMENT_NAME      Default: gpt-4.1
  DIAGNOSIS_AGENT_NAME / KNOWLEDGE_AGENT_NAME / ACTION_AGENT_NAME  (optional overrides)

Run:
  python -m app.backend.bootstrap_agents          # idempotent upsert
  python -m app.backend.bootstrap_agents --reset  # delete + recreate
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=False)

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
MODEL = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1")
DIAGNOSIS_AGENT_NAME = os.getenv("DIAGNOSIS_AGENT_NAME", "signal-to-service-diagnosis-agent")
KNOWLEDGE_AGENT_NAME = os.getenv("KNOWLEDGE_AGENT_NAME", "signal-to-service-knowledge-agent")
ACTION_AGENT_NAME = os.getenv("ACTION_AGENT_NAME", "signal-to-service-action-agent")
CACHE_PATH = ROOT / "agents.json"


DIAGNOSIS_INSTRUCTIONS = """\
You are a predictive-maintenance reliability engineer. The user message contains
an asset descriptor and a telemetry summary (vibration in mm/s, temperature in C,
current in A) with nominal/warn/alarm thresholds and current/peak values.

Interpret the signals, classify the most likely failure mode, and estimate
criticality and remaining useful life. Return ONLY a JSON object (no prose, no
code fences) with exactly these fields:

  - failure_mode  (one of: "bearing", "overheating", "overcurrent", "imbalance")
  - criticality   (one of: "low", "medium", "high")
  - rul_days      (integer, estimated remaining useful life in days)
  - confidence    (number 0..1)
  - rationale     (max 30 words, which signals drove the classification)

Base failure_mode on the channel that has breached its thresholds:
vibration-dominant with rising temperature → "bearing"; temperature-dominant →
"overheating"; current-dominant → "overcurrent"; vibration-only 1x-type rise →
"imbalance". Higher criticality when the alarm threshold is breached."""

KNOWLEDGE_INSTRUCTIONS = """\
You are a maintenance knowledge assistant. The user message contains a diagnosed
failure mode and several retrieved SOP passages, each tagged with a doc_id, title,
section and source file.

Select the single most relevant SOP for the failure mode and return ONLY a JSON
object (no prose, no code fences) with exactly these fields:

  - sop_id     (the doc_id of the chosen SOP, copied verbatim)
  - title      (the SOP title)
  - citation   (the source filename of the chosen SOP, copied verbatim)
  - summary    (max 40 words, what the SOP tells the technician to do)
  - key_steps  (array of 3-5 short strings, the core corrective steps)

Only use information present in the retrieved passages. Never invent a doc_id or
source that is not in the input."""

ACTION_INSTRUCTIONS = """\
You are a field-service dispatcher. Given an asset, a diagnosis and the chosen
SOP, write a concise maintenance work-order summary (max 3 sentences) that tells
the assigned technician what to do and which SOP to follow. Return plain text
only — no JSON, no code fences."""


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
        print(f"[bootstrap] deleted prompt agent {name}")
    except Exception as ex:
        print(f"[bootstrap] no prior prompt agent '{name}' (ok): {ex.__class__.__name__}")


def ensure_persistent_agents(reset: bool = False) -> Dict[str, str]:
    project = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential())

    specs = [
        (DIAGNOSIS_AGENT_NAME, DIAGNOSIS_INSTRUCTIONS, "Classifies the failure mode, criticality and RUL from telemetry."),
        (KNOWLEDGE_AGENT_NAME, KNOWLEDGE_INSTRUCTIONS, "Summarises and cites the correct SOP from retrieved passages."),
        (ACTION_AGENT_NAME, ACTION_INSTRUCTIONS, "Drafts the technician work-order summary."),
    ]

    if reset:
        for name, _, _ in specs:
            _delete_prompt_agent(project, name)

    out: Dict[str, str] = {"agent_kind": "prompt-agent-v2", "model": MODEL}
    for name, instructions, description in specs:
        agent = project.agents.create_version(
            agent_name=name,
            definition=PromptAgentDefinition(model=MODEL, instructions=instructions),
            description=description,
        )
        print(f"[bootstrap] agent: name={agent.name} version={agent.version}")
        out[name] = agent.name

    _save_cache(out)
    return out


if __name__ == "__main__":
    reset = "--reset" in sys.argv
    ids = ensure_persistent_agents(reset=reset)
    print(json.dumps(ids, indent=2))
