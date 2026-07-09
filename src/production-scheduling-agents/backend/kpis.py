"""KPI computation for the dashboard strip.

Deliberately simple, transparent arithmetic over the current schedule — the
point is a number that visibly moves when the agents act, not plant accounting.
"""

from __future__ import annotations

from .plant import Plant


def compute(plant: Plant) -> dict:
    slots = plant.schedule.slots
    horizon = max((s.end_hour for s in slots), default=8.0)

    # Idle time: gaps inside the horizon on machines that have work assigned.
    idle_hours = 0.0
    for machine_id in plant.machines:
        mine = sorted((s for s in slots if s.machine_id == machine_id), key=lambda s: s.start_hour)
        if not mine:
            continue
        cursor = 0.0
        for slot in mine:
            idle_hours += max(0.0, slot.start_hour - cursor)
            cursor = max(cursor, slot.end_hour)
        idle_hours += max(0.0, horizon - cursor)

    # Adherence: share of scheduled orders finishing by their due time.
    scheduled = [s for s in slots if s.order_id in plant.orders]
    on_time = sum(1 for s in scheduled if s.end_hour <= plant.orders[s.order_id].due_hours)
    adherence_pct = round(100.0 * on_time / len(scheduled)) if scheduled else 100

    return {
        "schedule_version": plant.schedule.version,
        "idle_hours": round(idle_hours, 1),
        "adherence_pct": adherence_pct,
    }
