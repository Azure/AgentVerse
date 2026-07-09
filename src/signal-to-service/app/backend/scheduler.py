"""Field-service scheduler mock.

A tiny roster of technicians with skills and availability windows. The Action
agent calls ``assign_technician(required_skill)`` to pick the best-matching,
earliest-available technician for the work order.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

TECHNICIANS: List[Dict[str, Any]] = [
    {
        "id": "tech-01",
        "name": "Marta Ruiz",
        "skills": ["rotating-equipment", "mechanical"],
        "next_slot_hours": 2,
        "shift": "day",
    },
    {
        "id": "tech-02",
        "name": "David Okafor",
        "skills": ["electrical", "rotating-equipment"],
        "next_slot_hours": 4,
        "shift": "day",
    },
    {
        "id": "tech-03",
        "name": "Yuki Tanaka",
        "skills": ["hvac", "electrical"],
        "next_slot_hours": 6,
        "shift": "late",
    },
]


def list_technicians() -> List[Dict[str, Any]]:
    return TECHNICIANS


def assign_technician(required_skill: str) -> Optional[Dict[str, Any]]:
    """Return the earliest-available technician holding ``required_skill``.

    Falls back to the earliest-available technician of any skill if none match,
    so the demo always produces a schedule.
    """
    matches = [t for t in TECHNICIANS if required_skill in t["skills"]]
    pool = matches or TECHNICIANS
    chosen = min(pool, key=lambda t: t["next_slot_hours"])
    slot = datetime.now(timezone.utc) + timedelta(hours=chosen["next_slot_hours"])
    return {
        "technician_id": chosen["id"],
        "technician": chosen["name"],
        "skills": chosen["skills"],
        "skill_matched": required_skill in chosen["skills"],
        "scheduled_for": slot.isoformat(timespec="minutes"),
        "eta_hours": chosen["next_slot_hours"],
    }
