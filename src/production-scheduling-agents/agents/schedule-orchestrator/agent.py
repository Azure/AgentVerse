"""schedule-orchestrator — decide how the plant responds to a disruption.

Flow: guardrail short-circuit -> Foundry agent (reasons + explains) -> policy
gate (deterministic code enforces the rules the LLM is only asked to follow).
The gate is the demo's trust story: no unvalidated schedule can ever ship,
whatever the model says.
"""

from __future__ import annotations

import os
from pathlib import Path

from agents.shared import foundry
from agents.shared.models import DisruptionEvent, Schedule, SchedulingDecision, ScoredScenario

from .schemas import OrchestratorInput

AGENT_DIR = Path(__file__).resolve().parent


def _threshold() -> float:
    return float(os.getenv("AUTO_APPLY_CONFIDENCE_THRESHOLD", "0.8"))


def decide(
    disruption: DisruptionEvent,
    scenarios: list[ScoredScenario],
    active_schedule: Schedule | None = None,
) -> SchedulingDecision:
    """Return the final, policy-enforced scheduling decision for one disruption."""

    # Guardrail short-circuit: a flagged event never reaches the LLM at all —
    # the injected text must not appear in any prompt.
    if disruption.security_flag:
        return SchedulingDecision(
            decision="reject",
            chosen_scenario_id=None,
            confidence=1.0,
            rationale=(
                "A free-text field on this event (e.g. the operator comment) was "
                "flagged as a manipulation attempt by the input guardrail. No "
                "schedule change was made; the event has been logged for review."
            ),
            escalated=False,
            options_for_planner=[],
            security_flag=True,
        )

    payload = OrchestratorInput(
        disruption=disruption,
        scenarios=scenarios,
        active_schedule=active_schedule or Schedule(),
    )
    raw = foundry.run_agent(AGENT_DIR, payload, SchedulingDecision, fixture_key=disruption.id)
    return _apply_policy_gate(raw, disruption, scenarios)


def _apply_policy_gate(
    raw: SchedulingDecision,
    disruption: DisruptionEvent,
    scenarios: list[ScoredScenario],
) -> SchedulingDecision:
    """Enforce the escalation policy on the LLM's proposal.

    The LLM reasons and explains; this code decides what is allowed:
      - auto-apply requires: chosen scenario exists, has 0 hard-constraint
        violations, confidence >= threshold, and no tier-1 SLA in the trade-off;
      - escalation requires at least 2 presentable options;
      - anything that can satisfy neither is rejected.
    """
    by_id = {s.id: s for s in scenarios}
    feasible = [s for s in scenarios if s.hard_constraint_violations == 0]
    tier1_at_stake = disruption.tier1_sla_hours_remaining is not None

    def _escalate_or_reject(base: SchedulingDecision, reasons: list[str]) -> SchedulingDecision:
        note = " [Policy gate: " + "; ".join(reasons) + ".]"
        options = base.options_for_planner or [
            f"{s.id}: {s.tradeoff_summary}" for s in feasible
        ]
        if len(options) >= 2:
            return base.model_copy(update={
                "decision": "escalate_to_planner",
                "chosen_scenario_id": None,
                "escalated": True,
                "options_for_planner": options,
                "rationale": base.rationale + note,
                "security_flag": False,
            })
        return base.model_copy(update={
            "decision": "reject",
            "chosen_scenario_id": None,
            "escalated": False,
            "options_for_planner": [],
            "rationale": base.rationale + note + " No two feasible options to present; no change applied.",
            "security_flag": False,
        })

    if raw.decision == "auto_reschedule":
        reasons: list[str] = []
        chosen = by_id.get(raw.chosen_scenario_id or "")
        if chosen is None:
            reasons.append("chosen scenario is not among the validated scenarios")
        elif chosen.hard_constraint_violations > 0:
            reasons.append("chosen scenario violates hard constraints")
        if raw.confidence < _threshold():
            reasons.append(f"confidence {raw.confidence:.2f} below the auto-apply threshold {_threshold():.2f}")
        if tier1_at_stake:
            reasons.append("a tier-1 customer SLA is part of the trade-off")
        if reasons:
            return _escalate_or_reject(raw, reasons)
        return raw.model_copy(update={"escalated": False, "security_flag": False})

    if raw.decision == "escalate_to_planner":
        options = raw.options_for_planner or [f"{s.id}: {s.tradeoff_summary}" for s in feasible]
        if len(options) < 2:
            return _escalate_or_reject(raw, ["escalation needs at least two options"])
        return raw.model_copy(update={
            "chosen_scenario_id": None,
            "escalated": True,
            "options_for_planner": options,
            "security_flag": False,
        })

    # reject
    return raw.model_copy(update={
        "chosen_scenario_id": None,
        "escalated": False,
        "options_for_planner": [],
        "security_flag": False,
    })
