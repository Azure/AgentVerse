"""Typed I/O contract for schedule-orchestrator.

Input: the classified disruption + the simulator's validated scenarios + the
active schedule. Output: `SchedulingDecision` (shared/models.py) — parsed from
the LLM first, then enforced by the policy gate in agent.py.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from agents.shared.models import (
    DisruptionEvent,
    Schedule,
    SchedulingDecision,
    ScoredScenario,
)

__all__ = ["OrchestratorInput", "SchedulingDecision"]


class OrchestratorInput(BaseModel):
    disruption: DisruptionEvent
    scenarios: list[ScoredScenario] = Field(default_factory=list)
    active_schedule: Schedule = Field(default_factory=Schedule)
