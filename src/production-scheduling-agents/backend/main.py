"""FastAPI backend: streams the scheduling control loop to the planner dashboard.

Endpoints:
  GET  /api/state           current schedule, machines, orders, KPIs, counters
  GET  /api/run/{key}       run one scripted disruption; streams pipeline events (SSE)
  POST /api/choose          answer a pending escalation with {"scenario_id": "SCN-A"}
  POST /api/reset           fresh plant, version 1, counters cleared
  /                         serves ../frontend (the dashboard)

Run:  uvicorn backend.main:app --port 8000
Mode: replay (no Azure) unless PROJECT_ENDPOINT is set — same as the CLI.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Iterator, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agents.shared import foundry
from agents.shared.models import ScoredScenario

from .disruptions import RAW_DISRUPTIONS
from .kpis import compute as compute_kpis
from .pipeline import PipelineResult, run_pipeline
from .plant import Plant

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="Production Scheduling AI Agents")


class _State:
    """One demo session (single plant — this is a demo, not a multi-tenant app)."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.plant = Plant()
        self.pending_scenarios: dict[str, ScoredScenario] = {}
        self.counters = {
            "disruptions_handled": 0,
            "auto_applied": 0,
            "escalations": 0,
            "rejected": 0,
            "last_adjust_seconds": None,
        }


STATE = _State()


def _snapshot() -> dict:
    return {
        "mode": "replay" if foundry.replay_mode() else "live",
        "machines": [m.model_dump() for m in STATE.plant.machines.values()],
        "orders": {o.id: o.model_dump() for o in STATE.plant.orders.values()},
        "schedule": STATE.plant.schedule.model_dump(),
        "kpis": compute_kpis(STATE.plant),
        "counters": STATE.counters,
        "disruptions": sorted(RAW_DISRUPTIONS),
    }


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


@app.get("/api/state")
def get_state() -> dict:
    return _snapshot()


@app.post("/api/reset")
def reset() -> dict:
    STATE.reset()
    return _snapshot()


@app.get("/api/run/{key}")
def run_disruption(key: str) -> StreamingResponse:
    if key not in RAW_DISRUPTIONS:
        raise HTTPException(404, f"Unknown disruption '{key}'. Options: {sorted(RAW_DISRUPTIONS)}")

    # In replay mode agent responses are instant; pace events so the audience
    # can watch the agents "think". Live mode paces itself.
    delay = float(os.getenv("REPLAY_EVENT_DELAY", "0.8")) if foundry.replay_mode() else 0.0

    def events() -> Iterator[str]:
        started = time.monotonic()
        result = PipelineResult()
        STATE.pending_scenarios = {}
        try:
            for event in run_pipeline(key, STATE.plant, result=result):
                if event["type"] == "escalation":
                    STATE.pending_scenarios = {s.id: s for s in result.scenarios}
                yield _sse(event)
                if delay and event["type"].startswith("agent_"):
                    time.sleep(delay)
        except Exception as exc:  # surface failures to the UI instead of a dead stream
            yield _sse({"type": "error", "message": str(exc)})
            return

        decision = result.decision
        STATE.counters["disruptions_handled"] += 1
        if decision is not None:
            if decision.decision == "auto_reschedule":
                STATE.counters["auto_applied"] += 1
            elif decision.decision == "escalate_to_planner":
                STATE.counters["escalations"] += 1
            else:
                STATE.counters["rejected"] += 1
        STATE.counters["last_adjust_seconds"] = round(time.monotonic() - started, 1)
        yield _sse({"type": "state", "payload": _snapshot()})

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache"})


class Choice(BaseModel):
    scenario_id: str


@app.post("/api/choose")
def choose(choice: Choice) -> dict:
    scenario: Optional[ScoredScenario] = STATE.pending_scenarios.get(choice.scenario_id)
    if scenario is None:
        raise HTTPException(409, f"No pending escalation offers scenario '{choice.scenario_id}'.")
    schedule = STATE.plant.apply_scenario(scenario)  # re-validates: last line of defense
    STATE.pending_scenarios = {}
    return {
        "applied_scenario": scenario.id,
        "schedule_version": schedule.version,
        "notifications": [
            f"{m.machine_id}: {m.order_id} now +{m.start_hour:.1f}h-+{m.end_hour:.1f}h"
            for m in scenario.moves
        ],
        "state": _snapshot(),
    }


# Static dashboard last, so /api/* wins the routing.
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
