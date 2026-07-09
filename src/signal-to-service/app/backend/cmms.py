"""CMMS mock + run state store (SQLite).

Two responsibilities:

  * **Run state** — the server-side record that carries a HITL run across the
    two SSE phases (diagnose -> approve -> dispatch). The browser only ever
    holds a ``run_id``; the approved proposal lives here, so it cannot be
    tampered with client-side.
  * **Work orders** — the mocked maintenance-management system the Action agent
    writes to (``create_work_order`` / ``get_work_order``), with an idempotency
    guarantee so approving the same run twice never creates two work orders.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "signal_to_service.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id        TEXT PRIMARY KEY,
                asset_id      TEXT NOT NULL,
                mode          TEXT NOT NULL,
                status        TEXT NOT NULL,
                anomaly       TEXT,
                diagnosis     TEXT,
                sop           TEXT,
                proposal      TEXT,
                decision      TEXT,
                decision_by   TEXT,
                decision_reason TEXT,
                decided_at    TEXT,
                work_order_id TEXT,
                created_at    TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS work_orders (
                work_order_id TEXT PRIMARY KEY,
                run_id        TEXT NOT NULL,
                asset_id      TEXT NOT NULL,
                title         TEXT NOT NULL,
                priority      TEXT NOT NULL,
                sop_id        TEXT,
                technician    TEXT,
                scheduled_for TEXT,
                summary       TEXT,
                status        TEXT NOT NULL,
                created_at    TEXT NOT NULL
            );
            """
        )


def _dumps(v: Any) -> Optional[str]:
    return None if v is None else json.dumps(v, ensure_ascii=False)


def _loads(v: Optional[str]) -> Any:
    return None if v in (None, "") else json.loads(v)


# --------------------------------------------------------------------------- runs

def create_run(asset_id: str, mode: str, anomaly: Any) -> str:
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO runs (run_id, asset_id, mode, status, anomaly, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (run_id, asset_id, mode, "diagnosing", _dumps(anomaly), _now()),
        )
    return run_id


def save_diagnosis(run_id: str, diagnosis: Any, sop: Any, proposal: Any) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE runs SET diagnosis=?, sop=?, proposal=?, status=? WHERE run_id=?",
            (_dumps(diagnosis), _dumps(sop), _dumps(proposal), "awaiting_approval", run_id),
        )


def record_decision(run_id: str, decision: str, reason: str, by: str) -> None:
    status = "approved" if decision == "approve" else "rejected"
    with get_conn() as conn:
        conn.execute(
            "UPDATE runs SET decision=?, decision_reason=?, decision_by=?, decided_at=?, status=? "
            "WHERE run_id=?",
            (decision, reason, by, _now(), status, run_id),
        )


def set_status(run_id: str, status: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE runs SET status=? WHERE run_id=?", (status, run_id))


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
    if row is None:
        return None
    d = dict(row)
    for k in ("anomaly", "diagnosis", "sop", "proposal"):
        d[k] = _loads(d.get(k))
    return d


# --------------------------------------------------------------------- work orders

def create_work_order(
    run_id: str,
    asset_id: str,
    title: str,
    priority: str,
    sop_id: Optional[str],
    technician: Optional[str],
    scheduled_for: Optional[str],
    summary: str,
) -> Dict[str, Any]:
    """Idempotent per run: if the run already has a work order, return it."""
    run = get_run(run_id)
    if run and run.get("work_order_id"):
        existing = get_work_order(run["work_order_id"])
        if existing:
            return existing
    work_order_id = f"WO-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO work_orders (work_order_id, run_id, asset_id, title, priority, "
            "sop_id, technician, scheduled_for, summary, status, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (work_order_id, run_id, asset_id, title, priority, sop_id, technician,
             scheduled_for, summary, "scheduled", _now()),
        )
        conn.execute(
            "UPDATE runs SET work_order_id=?, status=? WHERE run_id=?",
            (work_order_id, "dispatched", run_id),
        )
    return get_work_order(work_order_id)  # type: ignore[return-value]


def get_work_order(work_order_id: str) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM work_orders WHERE work_order_id=?", (work_order_id,)
        ).fetchone()
    return dict(row) if row else None
