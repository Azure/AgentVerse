"""The scheduling control loop: Sense -> Simulate -> Decide -> Act.

`run_pipeline()` is a generator of plain-dict events (`agent_start`,
`agent_log`, `agent_done`, `escalation`, `schedule_updated`, `decision`,
`done`) consumed identically by the CLI runner, the eval gate, and the SSE
backend. The monitor and dispatcher are deterministic code by design; the
simulator and orchestrator are the LLM agents.
"""

from __future__ import annotations

import importlib
from typing import Iterator, Optional

from agents.shared.models import SchedulingDecision, ScoredScenario

from .disruptions import RAW_DISRUPTIONS, classify
from .plant import Plant

_simulator = importlib.import_module("agents.scenario-simulator.agent")
_orchestrator = importlib.import_module("agents.schedule-orchestrator.agent")


class PipelineResult:
    """Filled in as the generator runs; inspect it after consuming the events."""

    def __init__(self) -> None:
        self.decision: Optional[SchedulingDecision] = None
        self.scenarios: list[ScoredScenario] = []
        self.schedule_changed: bool = False


def run_pipeline(
    disruption_key: str,
    plant: Plant,
    choose: Optional[str] = None,
    result: Optional[PipelineResult] = None,
) -> Iterator[dict]:
    """Run one disruption through the loop.

    `disruption_key` is a key of RAW_DISRUPTIONS. `choose` pre-answers an
    escalation with a scenario id (the CLI's --choose; the UI supplies it from
    the planner's click). `result` collects the outcome for the caller.
    """
    result = result if result is not None else PipelineResult()

    # ---- Sense (constraint-monitor: deterministic code) ---------------------------
    yield {"type": "agent_start", "agent": "constraint-monitor"}
    disruption = classify(RAW_DISRUPTIONS[disruption_key])
    plant.apply_disruption(disruption)
    yield {
        "type": "agent_done", "agent": "constraint-monitor",
        "payload": disruption.model_dump(),
    }

    # A flagged event never reaches an LLM: straight to the decision.
    if disruption.security_flag:
        yield {"type": "agent_start", "agent": "schedule-orchestrator"}
        decision = _orchestrator.decide(disruption, [], plant.schedule)
        result.decision = decision
        yield {"type": "agent_done", "agent": "schedule-orchestrator", "payload": decision.model_dump()}
        yield {"type": "decision", "payload": decision.model_dump()}
        yield {"type": "done", "schedule_version": plant.schedule.version}
        return

    # ---- Simulate (scenario-simulator: LLM + feasibility gate) ---------------------
    yield {"type": "agent_start", "agent": "scenario-simulator"}
    scenarios, sim_log = _simulator.simulate(
        disruption, plant.schedule, plant.snapshot(), plant.validate_moves
    )
    result.scenarios = scenarios
    for line in sim_log:
        yield {"type": "agent_log", "agent": "scenario-simulator", "message": line}
    yield {
        "type": "agent_done", "agent": "scenario-simulator",
        "payload": {"scenarios": [s.model_dump() for s in scenarios]},
    }

    # ---- Decide (schedule-orchestrator: LLM + policy gate) --------------------------
    yield {"type": "agent_start", "agent": "schedule-orchestrator"}
    decision = _orchestrator.decide(disruption, scenarios, plant.schedule)
    result.decision = decision
    yield {"type": "agent_done", "agent": "schedule-orchestrator", "payload": decision.model_dump()}

    chosen: Optional[ScoredScenario] = None
    if decision.decision == "auto_reschedule":
        chosen = next(s for s in scenarios if s.id == decision.chosen_scenario_id)
    elif decision.decision == "escalate_to_planner":
        yield {
            "type": "escalation",
            "options": decision.options_for_planner,
            "rationale": decision.rationale,
        }
        if choose:
            chosen = next((s for s in scenarios if s.id == choose), None)
            if chosen is None:
                yield {"type": "agent_log", "agent": "schedule-dispatcher",
                       "message": f"Planner chose unknown scenario '{choose}'; nothing applied."}

    yield {"type": "decision", "payload": decision.model_dump()}

    # ---- Act (schedule-dispatcher: deterministic code) ------------------------------
    if chosen is not None:
        yield {"type": "agent_start", "agent": "schedule-dispatcher"}
        schedule = plant.apply_scenario(chosen)  # re-validates: last line of defense
        result.schedule_changed = True
        yield {
            "type": "agent_done", "agent": "schedule-dispatcher",
            "payload": {
                "published": True,
                "schedule_version": schedule.version,
                "applied_scenario": chosen.id,
                "notifications": [
                    f"{m.machine_id}: {m.order_id} now +{m.start_hour:.1f}h-+{m.end_hour:.1f}h"
                    for m in chosen.moves
                ],
            },
        }
        yield {"type": "schedule_updated", "schedule": schedule.model_dump()}

    yield {"type": "done", "schedule_version": plant.schedule.version}
