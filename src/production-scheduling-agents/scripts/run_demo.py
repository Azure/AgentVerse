"""Run one disruption through the scheduling loop from the CLI (no UI).

Usage (from the demo root):

    python scripts/run_demo.py --disruption machine_down
    python scripts/run_demo.py --disruption material_delay --choose SCN-A
    python scripts/run_demo.py --disruption prompt_injection
    python scripts/run_demo.py --all

Replay mode by default (no Azure). With PROJECT_ENDPOINT set it drives the live
Foundry agents; add --record to save the live responses as replay fixtures.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.shared import foundry  # noqa: E402
from backend.disruptions import RAW_DISRUPTIONS  # noqa: E402
from backend.pipeline import PipelineResult, run_pipeline  # noqa: E402
from backend.plant import Plant  # noqa: E402


def print_schedule(plant: Plant, title: str) -> None:
    print(f"\n== {title} (schedule v{plant.schedule.version}) " + "=" * 30)
    for machine_id in plant.machines:
        slots = sorted(
            (s for s in plant.schedule.slots if s.machine_id == machine_id),
            key=lambda s: s.start_hour,
        )
        row = "  ".join(f"{s.order_id}[+{s.start_hour:g}h..+{s.end_hour:g}h]" for s in slots)
        status = plant.machines[machine_id].status
        print(f"  {machine_id:<10} ({status:<8}) {row or '-'}")


def run_one(key: str, choose: str | None) -> bool:
    plant = Plant()
    print(f"\n{'#' * 70}\n# Disruption: {key}\n{'#' * 70}")
    print_schedule(plant, "Before")

    result = PipelineResult()
    for event in run_pipeline(key, plant, choose=choose, result=result):
        kind = event["type"]
        if kind == "agent_start":
            print(f"\n>> {event['agent']} ...")
        elif kind == "agent_log":
            print(f"   | {event['message']}")
        elif kind == "agent_done" and event["agent"] == "schedule-orchestrator":
            p = event["payload"]
            print(f"   decision: {p['decision']}  (confidence {p['confidence']:.2f})")
            print(f"   rationale: {p['rationale']}")
        elif kind == "escalation":
            print("\n   ESCALATED TO PLANNER — options:")
            for option in event["options"]:
                print(f"     * {option}")
            if not choose:
                print("   (re-run with --choose <SCN-id> to answer as the planner)")
        elif kind == "agent_done" and event["agent"] == "schedule-dispatcher":
            p = event["payload"]
            print(f"   published v{p['schedule_version']} (scenario {p['applied_scenario']})")
            for note in p["notifications"]:
                print(f"     -> {note}")

    print_schedule(plant, "After")
    decision = result.decision
    print(f"\nOutcome: {decision.decision}"
          f"{' [security flag]' if decision.security_flag else ''}"
          f" | schedule {'changed' if result.schedule_changed else 'unchanged'}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--disruption", choices=sorted(RAW_DISRUPTIONS), help="Which scripted disruption to inject.")
    parser.add_argument("--choose", help="Answer an escalation with this scenario id (e.g. SCN-A).")
    parser.add_argument("--all", action="store_true", help="Run every scripted disruption in sequence.")
    parser.add_argument("--record", action="store_true",
                        help="Live mode only: save agent responses as replay fixtures.")
    args = parser.parse_args()

    if args.record:
        if foundry.replay_mode():
            parser.error("--record needs a live run: set PROJECT_ENDPOINT first.")
        os.environ["RECORD_FIXTURES"] = "true"

    keys = sorted(RAW_DISRUPTIONS) if args.all else [args.disruption] if args.disruption else None
    if not keys:
        parser.error("pass --disruption <key> or --all")

    mode = "replay (no Azure)" if foundry.replay_mode() else "live (Foundry Agents)"
    print(f"Mode: {mode}")
    for key in keys:
        run_one(key, args.choose)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
