"""Domain models shared by every agent and the backend.

These are the demo's single vocabulary: the plant, disruptions, scenarios, and
decisions. Every agent's typed I/O (schemas.py) builds on these.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

DecisionKind = Literal["auto_reschedule", "escalate_to_planner", "reject"]
DisruptionKind = Literal["machine_down", "material_delay", "rush_order"]
Severity = Literal["low", "medium", "high"]


class Order(BaseModel):
    id: str
    product: str
    quantity: int = 1
    run_hours: float = 1.0
    due_hours: float = Field(description="Hours from now until the order is due.")
    customer_tier: Literal["tier1", "standard"] = "standard"
    material: Optional[str] = None


class ScheduleSlot(BaseModel):
    order_id: str
    machine_id: str
    start_hour: float
    end_hour: float
    changeover_minutes: int = 0


class Schedule(BaseModel):
    version: int = 1
    slots: list[ScheduleSlot] = Field(default_factory=list)


class DisruptionEvent(BaseModel):
    """A classified disruption. Emitted by the constraint monitor (plain code in
    this demo); `security_flag` is set by the prompt-injection guardrail when a
    free-text field (e.g. an MES operator comment) looks like manipulation."""

    # Raw feeds carry extra fields (alternatives, delay_hours, ...) that agents
    # may reference in prose; keep them rather than dropping them.
    model_config = ConfigDict(extra="allow")

    id: str
    type: DisruptionKind
    severity: Severity = "medium"
    affected_orders: list[str] = Field(default_factory=list)
    hard_constraints_hit: list[str] = Field(default_factory=list)
    soft_constraints_hit: list[str] = Field(default_factory=list)
    operator_comment: Optional[str] = None
    tier1_sla_hours_remaining: Optional[float] = None
    security_flag: bool = False


class Move(BaseModel):
    """One structured schedule change: where an order runs and when. Scenarios
    carry these so the feasibility checker can validate them and the dispatcher
    can apply them; `schedule_delta` is the human-readable rendering."""

    order_id: str
    machine_id: str
    start_hour: float
    end_hour: float


class Machine(BaseModel):
    id: str
    name: str = ""
    capabilities: list[str] = Field(default_factory=list, description="Product types it can run.")
    status: Literal["running", "idle", "down", "maintenance"] = "idle"
    available_from_hour: float = 0.0


class MaterialStatus(BaseModel):
    id: str
    available: bool = True
    eta_hours: float = 0.0


class PlantSnapshot(BaseModel):
    """What the simulator sees: the plant state the moment a disruption lands."""

    machines: list[Machine] = Field(default_factory=list)
    orders: list[Order] = Field(default_factory=list)
    materials: list[MaterialStatus] = Field(default_factory=list)
    changeover_minutes: dict[str, int] = Field(
        default_factory=dict, description="'product_a->product_b' -> setup minutes."
    )


class ScenarioScores(BaseModel):
    """Soft-constraint scores, each normalized 0..1 where higher is better."""

    changeover_cost: float = Field(ge=0, le=1)
    urgency_served: float = Field(ge=0, le=1)
    labor_balance: float = Field(ge=0, le=1)
    energy: float = Field(ge=0, le=1)


class ScoredScenario(BaseModel):
    """One alternative schedule, already validated by the deterministic
    feasibility check. `hard_constraint_violations` must be 0 for a scenario to
    ever be applied."""

    id: str
    description: str
    moves: list[Move] = Field(
        default_factory=list,
        description="Structured changes; validated by the feasibility checker, applied by the dispatcher.",
    )
    schedule_delta: list[str] = Field(
        default_factory=list,
        description="Human-readable moves, e.g. 'ORD-7712: CNC-102 -> CNC-104 @ +0.5h'.",
    )
    hard_constraint_violations: int = 0
    scores: ScenarioScores
    tradeoff_summary: str
    confidence: float = Field(ge=0, le=1)


class SchedulingDecision(BaseModel):
    """The orchestrator's output — the demo's central artifact.

    Cross-field invariants (auto requires a chosen scenario, escalation requires
    >= 2 options, ...) are deliberately NOT enforced here: the raw LLM output is
    parsed into this model first, then the deterministic policy gate in
    schedule-orchestrator/agent.py enforces and corrects them.
    """

    decision: DecisionKind
    chosen_scenario_id: Optional[str] = None
    confidence: float = Field(ge=0, le=1)
    rationale: str
    escalated: bool = False
    options_for_planner: list[str] = Field(default_factory=list)
    security_flag: bool = False
