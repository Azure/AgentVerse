"""scenario-simulator — propose and score alternative schedules.

Flow: Foundry agent proposes scenarios -> deterministic feasibility gate
re-validates every scenario's moves against the plant (machine capability,
downtime windows, material ETAs, overlaps). Infeasible scenarios are DISCARDED,
never repaired: the LLM proposes, the checker disposes.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from agents.shared import foundry
from agents.shared.models import DisruptionEvent, Move, PlantSnapshot, Schedule, ScoredScenario

from .schemas import SimulatorInput, SimulatorOutput

AGENT_DIR = Path(__file__).resolve().parent

# The feasibility checker is injected (backend/plant.py provides it) so the
# agent stays decoupled from plant internals and trivially testable.
MoveValidator = Callable[[list[Move]], tuple[int, list[str]]]


def _max_scenarios() -> int:
    return int(os.getenv("MAX_SCENARIOS_PER_DISRUPTION", "3"))


def simulate(
    disruption: DisruptionEvent,
    active_schedule: Schedule,
    plant: PlantSnapshot,
    validate_moves: MoveValidator,
) -> tuple[list[ScoredScenario], list[str]]:
    """Return (feasible scenarios, log lines). Every returned scenario has been
    re-validated in code: `hard_constraint_violations` is the CHECKER's count
    (always 0 for survivors), not the LLM's claim."""
    payload = SimulatorInput(disruption=disruption, active_schedule=active_schedule, plant=plant)
    raw = foundry.run_agent(AGENT_DIR, payload, SimulatorOutput, fixture_key=disruption.id)

    feasible: list[ScoredScenario] = []
    log: list[str] = []
    for scenario in raw.scenarios[: _max_scenarios()]:
        count, reasons = validate_moves(scenario.moves)
        if count:
            log.append(f"{scenario.id} discarded by feasibility check: {'; '.join(reasons)}")
            continue
        feasible.append(scenario.model_copy(update={"hard_constraint_violations": 0}))
        log.append(f"{scenario.id} feasible: {scenario.tradeoff_summary}")
    return feasible, log
