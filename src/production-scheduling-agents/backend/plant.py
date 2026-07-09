"""The mock plant: state, disruption effects, and the deterministic feasibility
checker that stands in for a constraint solver.

This module is the demo's "hard constraints are never enforced by the LLM alone"
guarantee: every scenario the simulator proposes is validated here, and only
scenarios with zero violations can ever be applied.
"""

from __future__ import annotations

import json
from pathlib import Path

from agents.shared.models import (
    DisruptionEvent,
    Machine,
    MaterialStatus,
    Move,
    Order,
    PlantSnapshot,
    Schedule,
    ScheduleSlot,
    ScoredScenario,
)

DATA_FILE = Path(__file__).resolve().parent / "plant_data.json"


class Plant:
    def __init__(self, data: dict | None = None):
        data = data or json.loads(DATA_FILE.read_text(encoding="utf-8"))
        self.machines: dict[str, Machine] = {m["id"]: Machine.model_validate(m) for m in data["machines"]}
        self.orders: dict[str, Order] = {o["id"]: Order.model_validate(o) for o in data["orders"]}
        self.materials: dict[str, MaterialStatus] = {
            m["id"]: MaterialStatus.model_validate(m) for m in data["materials"]
        }
        self.changeover_minutes: dict[str, int] = dict(data["changeover_minutes"])
        self.schedule = Schedule(
            version=1,
            slots=[ScheduleSlot.model_validate(s) for s in data["initial_schedule"]],
        )

    # ---- state ------------------------------------------------------------------

    def snapshot(self) -> PlantSnapshot:
        return PlantSnapshot(
            machines=list(self.machines.values()),
            orders=list(self.orders.values()),
            materials=list(self.materials.values()),
            changeover_minutes=self.changeover_minutes,
        )

    def apply_disruption(self, event: DisruptionEvent) -> None:
        """Mutate plant state to reflect the disruption (the raw feed's effect)."""
        extra = event.model_extra or {}
        if event.type == "machine_down":
            machine = self.machines.get(extra.get("machine", ""))
            if machine:
                machine.status = "down"
                machine.available_from_hour = float(extra.get("estimated_downtime_minutes", 60)) / 60.0
        elif event.type == "material_delay":
            material = self.materials.get(extra.get("material", ""))
            if material:
                material.available = False
                material.eta_hours = float(extra.get("delay_hours", 4))
        elif event.type == "rush_order":
            order = extra.get("order")
            if isinstance(order, dict):
                new_order = Order.model_validate(order)
                self.orders[new_order.id] = new_order

    # ---- feasibility (the deterministic "solver") ---------------------------------

    def validate_moves(self, moves: list[Move]) -> tuple[int, list[str]]:
        """Check a scenario's moves against hard constraints. Returns
        (violation_count, reasons). Zero violations = the scenario may be applied."""
        violations: list[str] = []
        moved_orders = {m.order_id for m in moves}

        for move in moves:
            machine = self.machines.get(move.machine_id)
            order = self.orders.get(move.order_id)
            if machine is None:
                violations.append(f"{move.order_id}: unknown machine {move.machine_id}")
                continue
            if order is None:
                violations.append(f"unknown order {move.order_id}")
                continue
            if move.end_hour <= move.start_hour:
                violations.append(f"{move.order_id}: empty/negative time window")
            if order.product not in machine.capabilities:
                violations.append(
                    f"{move.order_id}: {machine.id} cannot run product '{order.product}' (tool compatibility)"
                )
            if machine.status in ("down", "maintenance") and move.start_hour < machine.available_from_hour:
                violations.append(
                    f"{move.order_id}: {machine.id} is {machine.status} until +{machine.available_from_hour:.2f}h"
                )
            if order.material:
                material = self.materials.get(order.material)
                if material and not material.available and move.start_hour < material.eta_hours:
                    violations.append(
                        f"{move.order_id}: material {order.material} not available before +{material.eta_hours:.1f}h"
                    )

        # No overlap on the same machine: against other moves and against
        # untouched slots of the current schedule.
        busy: list[tuple[str, float, float, str]] = [
            (m.machine_id, m.start_hour, m.end_hour, m.order_id) for m in moves
        ] + [
            (s.machine_id, s.start_hour, s.end_hour, s.order_id)
            for s in self.schedule.slots
            if s.order_id not in moved_orders
        ]
        busy.sort()
        for (m1, a1, b1, o1), (m2, a2, b2, o2) in zip(busy, busy[1:]):
            if m1 == m2 and a2 < b1:
                violations.append(f"overlap on {m1}: {o1} and {o2}")

        return len(violations), violations

    # ---- dispatch -----------------------------------------------------------------

    def apply_scenario(self, scenario: ScoredScenario) -> Schedule:
        """Apply a validated scenario: replace the moved orders' slots, bump the
        schedule version. Raises if the scenario doesn't validate — the last line
        of defense before 'publishing'."""
        count, reasons = self.validate_moves(scenario.moves)
        if count:
            raise ValueError(f"Refusing to apply scenario {scenario.id}: {reasons}")
        moved = {m.order_id for m in scenario.moves}
        slots = [s for s in self.schedule.slots if s.order_id not in moved] + [
            ScheduleSlot(order_id=m.order_id, machine_id=m.machine_id,
                         start_hour=m.start_hour, end_hour=m.end_hour)
            for m in scenario.moves
        ]
        slots.sort(key=lambda s: (s.machine_id, s.start_hour))
        self.schedule = Schedule(version=self.schedule.version + 1, slots=slots)
        return self.schedule
