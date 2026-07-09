"""Eval gate: run every golden disruption case through the FULL scheduling
pipeline (monitor -> simulator -> orchestrator -> dispatcher) and assert the
decision outcomes, not just that it ran.

Usage (from the demo root):

    python -m evals.run_evals

Runs in replay mode by default (no Azure needed — agent responses come from
agents/fixtures/). With PROJECT_ENDPOINT set it exercises the live Foundry
agents instead. Exits non-zero on any failure and writes evals/last_report.json
for the CI gate (.github/workflows/eval-on-pr.yml).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
DEMO_ROOT = EVALS_DIR.parent
sys.path.insert(0, str(DEMO_ROOT))

from backend.disruptions import RAW_DISRUPTIONS  # noqa: E402
from backend.pipeline import PipelineResult, run_pipeline  # noqa: E402
from backend.plant import Plant  # noqa: E402

# golden case id -> the scripted disruption that produces it
CASE_TO_DISRUPTION = {raw["id"]: key for key, raw in RAW_DISRUPTIONS.items()}


def check_case(case: dict) -> tuple[bool, list[str]]:
    disruption_key = CASE_TO_DISRUPTION[case["id"]]
    plant = Plant()
    result = PipelineResult()
    for _event in run_pipeline(disruption_key, plant, result=result):
        pass
    decision = result.decision

    chosen = next((s for s in result.scenarios if s.id == decision.chosen_scenario_id), None)
    actual = {
        "decision": decision.decision,
        "escalated": decision.escalated,
        "security_flag": decision.security_flag,
        "schedule_changed": result.schedule_changed,
        "hard_constraint_violations": chosen.hard_constraint_violations if chosen else 0,
        "min_scenarios_presented": len(decision.options_for_planner),
    }

    failures: list[str] = []
    for key, expected in case["expect"].items():
        got = actual.get(key)
        if key == "min_scenarios_presented":
            if got < expected:
                failures.append(f"{key}: expected >= {expected}, got {got}")
        elif got != expected:
            failures.append(f"{key}: expected {expected!r}, got {got!r}")
    return not failures, failures


def main() -> int:
    dataset = json.loads((EVALS_DIR / "golden_dataset.json").read_text(encoding="utf-8"))
    results = []
    for case in dataset["cases"]:
        try:
            passed, failures = check_case(case)
        except Exception as exc:  # a crash is a failing case, not a crashed gate
            passed, failures = False, [f"error: {exc}"]
        results.append({"id": case["id"], "passed": passed, "failures": failures})
        mark = "PASS" if passed else "FAIL"
        print(f"[{mark}] {case['id']}" + (f"  -> {'; '.join(failures)}" if failures else ""))

    pass_rate = sum(r["passed"] for r in results) / len(results) if results else 0.0
    report = {"pass_rate": f"{pass_rate:.0%}", "cases": results}
    (EVALS_DIR / "last_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nPass rate: {report['pass_rate']}  (report: evals/last_report.json)")
    return 0 if pass_rate == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
