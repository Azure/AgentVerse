"""Typed I/O contract for scenario-simulator.

Input: the disruption + active schedule + plant snapshot. Output: scored
scenarios — parsed from the LLM first, then every scenario's moves are
re-validated by the deterministic feasibility checker in agent.py (infeasible
scenarios are discarded, never repaired).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from agents.shared.models import (
    DisruptionEvent,
    PlantSnapshot,
    Schedule,
    ScoredScenario,
)

__all__ = ["SimulatorInput", "SimulatorOutput"]


class SimulatorInput(BaseModel):
    disruption: DisruptionEvent
    active_schedule: Schedule = Field(default_factory=Schedule)
    plant: PlantSnapshot = Field(default_factory=PlantSnapshot)


class SimulatorOutput(BaseModel):
    scenarios: list[ScoredScenario] = Field(default_factory=list)
