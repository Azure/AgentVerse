"""Signal-to-Service — FastAPI app (single container: UI at / + SSE API)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any, AsyncGenerator, Dict

# On Windows the default ProactorEventLoop is incompatible with aiohttp used by
# the azure-identity / azure-ai SDKs — switch to the selector loop before the
# agent modules import those SDKs.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import cmms, rag, telemetry
from .agents import orchestrate_diagnose, orchestrate_dispatch
from .sse import format_sse, sse_heartbeat

app = FastAPI(title="Signal-to-Service")

FRONTEND_PATH = Path(__file__).resolve().parent.parent / "frontend"

cmms.init_db()

app.mount("/static", StaticFiles(directory=str(FRONTEND_PATH)), name="static")

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}
_HEARTBEAT_SECONDS = 15


async def _stream_with_heartbeat(agen: AsyncGenerator[Dict[str, Any], None]) -> AsyncGenerator[str, None]:
    """Forward orchestrator events as SSE frames, emitting a heartbeat comment
    every _HEARTBEAT_SECONDS so ACA ingress keeps the stream open during long
    model/tool calls."""
    it = agen.__aiter__()
    while True:
        nxt = asyncio.ensure_future(it.__anext__())
        while True:
            done, _ = await asyncio.wait({nxt}, timeout=_HEARTBEAT_SECONDS)
            if nxt in done:
                break
            yield sse_heartbeat()
        try:
            event = nxt.result()
        except StopAsyncIteration:
            break
        event_type = event.pop("type")
        yield format_sse(event_type, event)


@app.get("/")
async def root():
    return FileResponse(FRONTEND_PATH / "index.html")


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "rag_backend": rag.backend_kind()}


@app.get("/api/assets")
async def api_assets():
    return telemetry.load_assets()


@app.get("/api/telemetry")
async def api_telemetry(asset: str, series: str = "healthy"):
    try:
        return telemetry.generate_series(asset, series)
    except KeyError:
        return JSONResponse({"error": "unknown asset"}, status_code=404)


@app.get("/api/diagnose")
async def api_diagnose(asset: str, series: str = "degrading"):
    """Phase A (SSE): create a run, diagnose, retrieve the SOP, await approval."""
    try:
        sdata = telemetry.generate_series(asset, series)
    except KeyError:
        return JSONResponse({"error": "unknown asset"}, status_code=404)
    run_id = cmms.create_run(asset, series, sdata.get("anomaly"))
    return StreamingResponse(
        _stream_with_heartbeat(orchestrate_diagnose(run_id, asset, series)),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@app.post("/api/approval")
async def api_approval(request: Request):
    """Record the human governance decision (approve | reject)."""
    body = await request.json()
    run_id = body.get("run_id")
    decision = body.get("decision")
    reason = body.get("reason", "")
    by = body.get("by", "shift-supervisor")
    if decision not in ("approve", "reject"):
        return JSONResponse({"error": "decision must be approve or reject"}, status_code=400)
    run = cmms.get_run(run_id)
    if run is None:
        return JSONResponse({"error": "unknown run"}, status_code=404)
    cmms.record_decision(run_id, decision, reason, by)
    return {"run_id": run_id, "decision": decision, "status": "approved" if decision == "approve" else "rejected"}


@app.get("/api/dispatch")
async def api_dispatch(run_id: str):
    """Phase B (SSE): after approval, create the work order + schedule."""
    return StreamingResponse(
        _stream_with_heartbeat(orchestrate_dispatch(run_id)),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@app.get("/api/run/{run_id}")
async def api_run(run_id: str):
    run = cmms.get_run(run_id)
    if run is None:
        return JSONResponse({"error": "unknown run"}, status_code=404)
    return run


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8767)
