"""Foundry hosted-agent entrypoint for the insurance claims orchestrator.

Wraps the existing multi-agent pipeline (``agents/orchestrator/agent.py::process_claim``
— the Microsoft Agent Framework ``SequentialBuilder`` workflow Intake -> Risk -> Compliance
-> Decision, with an automatic fallback to the legacy orchestrator) behind the Azure AI
Foundry Agent Server ``invocations`` protocol.

All domain logic — agent instructions, tools, Pydantic response schemas, compliance rules
and the deterministic prompt-injection guard — is reused unchanged; this module only adds
the HTTP hosting surface that Foundry expects.

Contract (POST /invocations):
    Request JSON::

        {
          "claim": {
            "policy_id": "POL-1001",
            "customer_id": "CUST-001",
            "incident_type": "collision",
            "description": "....",
            "estimated_amount": 1200,
            "image_b64": "<optional base64>",
            "claim_id": "<optional>"
          },
          "stream": false
        }

    Claim fields may also be supplied at the top level. When ``stream`` is false the
    response is the full decision object as JSON. When ``stream`` is true the response is
    Server-Sent Events: one ``progress`` event per pipeline-stage update, then a final
    ``result`` event carrying the full decision (mirrors the backend WebSocket contract).

Run locally::

    python agents/hosted/app.py   # -> http://0.0.0.0:8088/invocations
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from pathlib import Path

# Make the repo root importable so ``agents.*`` resolves whether this module is
# started as a script (``python agents/hosted/app.py``) or as ``python -m agents.hosted.app``.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

from azure.ai.agentserver.invocations import InvocationAgentServerHost

from agents.orchestrator.agent import process_claim

load_dotenv(override=False)

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger("insurance.hosted")

app = InvocationAgentServerHost()

# Export the agent's OTel spans (workflow.run / invoke_agent / chat / execute_tool)
# to Application Insights so each claim shows up in the Foundry project's Tracing tab.
#
# The Foundry hosted runtime installs a MeterProvider (runtime metrics land in the
# project's App Insights) but leaves the global *tracer* provider as a Proxy/NoOp, so a
# plain add_span_processor has nothing real to attach to. We therefore install a real
# SDK TracerProvider when needed. A secondary connection string enables dual-export so
# the same trace is visible BOTH in Foundry and in the demo's shared App Insights.
_appinsights_attached = False


def _attach_appinsights_exporter() -> None:
    global _appinsights_attached
    if _appinsights_attached:
        return
    _appinsights_attached = True

    conns: list[str] = []
    primary = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING", "").strip()
    if primary:
        conns.append(primary)
    secondary = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING_SECONDARY", "").strip()
    if secondary and secondary != primary:
        conns.append(secondary)
    if not conns:
        logger.warning("No APPLICATIONINSIGHTS_CONNECTION_STRING set; agent traces will not be exported")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

        provider = trace.get_tracer_provider()
        # The Foundry runtime already attaches its own exporter to the project's App
        # Insights (primary) on a real provider. In that case we must NOT re-export to
        # the primary (it would duplicate every span); we only add the extra targets.
        # If instead the global tracer is a Proxy/NoOp, the runtime is not exporting
        # traces, so we install our own provider and own ALL targets (incl. primary).
        runtime_exports_primary = hasattr(provider, "add_span_processor")
        if not runtime_exports_primary:
            logger.info("Global tracer provider is %s; installing an SDK TracerProvider for export", type(provider).__name__)
            provider = TracerProvider()
            trace.set_tracer_provider(provider)

        targets = [c for c in conns if c != primary]  # secondary/extra targets
        if not runtime_exports_primary and primary:
            targets.insert(0, primary)
        for conn in targets:
            provider.add_span_processor(BatchSpanProcessor(AzureMonitorTraceExporter(connection_string=conn)))
        logger.info("Attached %d Azure Monitor trace exporter(s) to %s (runtime_exports_primary=%s)", len(targets), type(provider).__name__, runtime_exports_primary)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not attach App Insights exporter: %s", exc)

    # Ensure the agent_framework gen_ai instrumentation is active so the spans are
    # actually created (idempotent with the in-process MAF observability setup).
    try:
        from agent_framework.observability import enable_instrumentation

        enable_instrumentation()
        logger.info("agent_framework instrumentation enabled (hosted)")
    except Exception as exc:  # noqa: BLE001
        logger.warning("enable_instrumentation failed (hosted): %s", exc)

    # This function fully owns observability for the hosted agent. Mark the in-process
    # MAF orchestrator's setup as already done so it does NOT call configure_azure_monitor
    # again — that would attach a second exporter to the primary connection and duplicate
    # every span in the Foundry project's App Insights.
    try:
        from agents.orchestrator import maf_agent

        maf_agent._OBSERVABILITY_CONFIGURED = True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not mark MAF observability as configured: %s", exc)


_CLAIM_FIELDS = (
    "policy_id",
    "customer_id",
    "incident_type",
    "description",
    "estimated_amount",
    "image_b64",
    "claim_id",
)


def _json(payload: dict, status_code: int = 200) -> Response:
    # default=str guards against any stray datetime and keeps Spanish text intact.
    return Response(
        json.dumps(payload, ensure_ascii=False, default=str),
        status_code=status_code,
        media_type="application/json",
    )


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


def _extract_claim(data: dict) -> dict:
    claim = dict(data.get("claim") or {})
    for field in _CLAIM_FIELDS:
        if field not in claim and field in data:
            claim[field] = data[field]
    claim.setdefault("claim_id", f"CLM-{uuid.uuid4().hex[:8].upper()}")
    return claim


@app.invoke_handler
async def handle(request: Request) -> Response:
    """POST /invocations — evaluate a claim through the multi-agent pipeline."""
    _attach_appinsights_exporter()
    try:
        data = await request.json()
    except Exception:  # noqa: BLE001
        return _json({"error": "Request body must be valid JSON"}, status_code=400)

    if not isinstance(data, dict):
        return _json({"error": "Request body must be a JSON object"}, status_code=400)

    claim = _extract_claim(data)
    if not claim.get("description"):
        return _json({"error": "Missing required field: description"}, status_code=400)

    if not bool(data.get("stream", False)):
        result = await process_claim(claim)
        return _json(result)

    async def event_stream():
        queue: asyncio.Queue = asyncio.Queue()

        async def progress_callback(stage: str, status: str, payload: dict):
            await queue.put(_sse("progress", {"stage": stage, "status": status, "data": payload}))

        async def run():
            try:
                result = await process_claim(claim, progress_callback=progress_callback)
                await queue.put(_sse("result", result))
            except Exception as exc:  # noqa: BLE001
                logger.exception("process_claim failed")
                await queue.put(_sse("error", {"error": str(exc)}))
            finally:
                await queue.put(None)

        task = asyncio.create_task(run())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
        finally:
            await task

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8088"))
    logger.info("Starting insurance claims hosted agent on 0.0.0.0:%s", port)
    app.run(host="0.0.0.0", port=port)
