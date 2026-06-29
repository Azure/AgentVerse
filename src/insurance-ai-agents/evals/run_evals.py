"""Golden-dataset evaluation harness.

Runs the multi-agent pipeline against a curated dataset of expected outcomes
and writes a structured report. Designed to run both locally and in CI.

Exit code:
    0 — all assertions passed
    1 — at least one regression detected

Usage:
    python -m evals.run_evals
    python -m evals.run_evals --dataset evals/golden_dataset.json --report evals/last_report.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make the project root importable when called as `python -m evals.run_evals`
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("evals")
logger.setLevel(logging.INFO)


# process_claim is imported lazily (only for --target local) so the Foundry target
# can run in a minimal environment without the agent-framework stack installed.
_PROCESS_CLAIM = None
_FOUNDRY_TOKEN = None

DEFAULT_FOUNDRY_ENDPOINT = (
    "https://ai-account-kzrzuypevlok4.services.ai.azure.com/api/projects/"
    "ai-project-ins-ai-foundry/agents/insurance-claims-orchestrator/endpoint/protocols/invocations"
)


def _local_process_claim():
    global _PROCESS_CLAIM
    if _PROCESS_CLAIM is None:
        from agents.orchestrator.agent import process_claim
        _PROCESS_CLAIM = process_claim
    return _PROCESS_CLAIM


def _foundry_token() -> str:
    global _FOUNDRY_TOKEN
    if _FOUNDRY_TOKEN is None:
        # Allow a pre-fetched token (e.g. `az account get-access-token`) so the
        # harness works in CI / minimal environments without DefaultAzureCredential.
        _FOUNDRY_TOKEN = os.environ.get("FOUNDRY_TOKEN")
    if _FOUNDRY_TOKEN is None:
        from azure.identity import DefaultAzureCredential
        _FOUNDRY_TOKEN = DefaultAzureCredential().get_token("https://ai.azure.com/.default").token
    return _FOUNDRY_TOKEN


async def _invoke_foundry(request: dict, endpoint: str, api_version: str) -> dict:
    """Invoke the deployed Foundry hosted agent (invocations protocol)."""
    import httpx

    url = f"{endpoint}?api-version={api_version}&agent_session_id=evalrunner0001"
    headers = {"Authorization": f"Bearer {_foundry_token()}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(url, headers=headers, json={"claim": request, "stream": False})
        resp.raise_for_status()
        return resp.json()


def _check_case(result: dict, expected: dict) -> tuple[bool, list[str]]:
    """Return (passed, list_of_failures)."""
    failures: list[str] = []

    # Decision check
    if "decision" in expected and result.get("decision") != expected["decision"]:
        failures.append(f"decision={result.get('decision')} but expected {expected['decision']}")

    if "decision_in" in expected and result.get("decision") not in expected["decision_in"]:
        failures.append(f"decision={result.get('decision')} not in {expected['decision_in']}")

    # Confidence
    if "min_confidence" in expected and result.get("confidence", 0) < expected["min_confidence"]:
        failures.append(f"confidence={result.get('confidence'):.2f} < min {expected['min_confidence']}")

    # Risk score
    risk_score = (result.get("risk_result") or {}).get("risk_score")
    if "max_risk_score" in expected and risk_score is not None and risk_score > expected["max_risk_score"]:
        failures.append(f"risk_score={risk_score} > max {expected['max_risk_score']}")

    if "min_risk_score" in expected and risk_score is not None and risk_score < expected["min_risk_score"]:
        failures.append(f"risk_score={risk_score} < min {expected['min_risk_score']}")

    # Security flag
    flagged = bool(result.get("security_flagged"))
    if expected.get("must_be_security_flagged") and not flagged:
        failures.append("security_flagged expected True, got False")
    if expected.get("must_not_be_security_flagged") and flagged:
        failures.append("security_flagged expected False, got True")

    return (len(failures) == 0, failures)


async def _run_one(case: dict, target: str, foundry_endpoint: str, api_version: str) -> dict:
    """Run a single eval case and return its row of the report."""
    name = case["name"]
    request = dict(case["request"])
    request["claim_id"] = f"EVAL-{name[:20].upper()}"
    expected = case["expected"]

    started = datetime.now(timezone.utc)
    try:
        if target == "foundry":
            result = await _invoke_foundry(request, foundry_endpoint, api_version)
        else:
            result = await _local_process_claim()(request)
    except Exception as e:  # noqa: BLE001
        return {
            "name": name,
            "passed": False,
            "error": str(e),
            "duration_ms": int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
        }

    passed, failures = _check_case(result, expected)
    return {
        "name": name,
        "passed": passed,
        "failures": failures,
        "decision": result.get("decision"),
        "confidence": result.get("confidence"),
        "risk_score": (result.get("risk_result") or {}).get("risk_score"),
        "fraud_probability": (result.get("risk_result") or {}).get("fraud_probability"),
        "security_flagged": bool(result.get("security_flagged")),
        "duration_ms": result.get("total_duration_ms"),
        "expected": expected,
    }


async def _run_all(dataset_path: Path, report_path: Path, target: str, foundry_endpoint: str, api_version: str) -> int:
    cases = json.loads(dataset_path.read_text(encoding="utf-8"))
    logger.info("Running %d eval cases against target=%s", len(cases), target)

    rows = []
    for case in cases:
        logger.info("→ %s", case["name"])
        row = await _run_one(case, target, foundry_endpoint, api_version)
        rows.append(row)
        status = "PASS" if row["passed"] else "FAIL"
        logger.info("   %s · decision=%s confidence=%s risk=%s flagged=%s",
                    status, row.get("decision"), row.get("confidence"),
                    row.get("risk_score"), row.get("security_flagged"))
        if not row["passed"]:
            for f in row.get("failures", []):
                logger.info("     - %s", f)

    passed = sum(1 for r in rows if r["passed"])
    total = len(rows)
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 3) if total else 0,
        "pipeline_version": "1.0.0",
        "target": target,
        "model": os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.4-mini"),
        "via_apim": os.environ.get("USE_APIM_GATEWAY", "false").lower() == "true",
        "results": rows,
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("\n=== Eval summary ===")
    logger.info("PASSED %d / %d (%.0f%%) — report: %s",
                passed, total, summary["pass_rate"] * 100, report_path)

    return 0 if passed == total else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run golden-dataset evals")
    parser.add_argument("--dataset", type=Path, default=ROOT / "evals" / "golden_dataset.json")
    parser.add_argument("--report", type=Path, default=ROOT / "evals" / "last_report.json")
    parser.add_argument("--target", choices=["local", "foundry"], default=os.environ.get("EVAL_TARGET", "local"),
                        help="local = in-process process_claim; foundry = invoke the deployed Foundry hosted agent")
    parser.add_argument("--foundry-endpoint", default=os.environ.get("FOUNDRY_AGENT_ENDPOINT", DEFAULT_FOUNDRY_ENDPOINT))
    parser.add_argument("--api-version", default="2025-11-15-preview")
    args = parser.parse_args()
    return asyncio.run(_run_all(args.dataset, args.report, args.target, args.foundry_endpoint, args.api_version))


if __name__ == "__main__":
    raise SystemExit(main())
