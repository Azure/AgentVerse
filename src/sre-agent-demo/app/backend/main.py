"""Azure SRE Agent demo — FastAPI single container (UI at / + JSON API).

Default mode is **guided replay**: deterministic, seeded incident investigations
served entirely from local data (no Azure calls), so the portal tab always renders.
The API is shaped so a future read-only *live* path (proxy to a dedicated sandbox
SRE Agent) can be added behind config without changing the frontend contract.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config, scenarios

app = FastAPI(title="Azure SRE Agent demo")

FRONTEND_PATH = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_PATH)), name="static")


@app.get("/")
async def root():
    return FileResponse(FRONTEND_PATH / "index.html")


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "mode": _mode()}


def _mode() -> str:
    # Live path is not enabled in this build; a configured resource id means a
    # future live proxy *would* engage. Until then we always serve replay.
    return "live" if config.live_configured() else "replay"


@app.get("/api/config")
async def api_config():
    """What the UI needs to render the right banner and rails (no secrets)."""
    return {
        "mode": _mode(),
        # Guided replay makes no Azure calls and takes no actions.
        "live_configured": config.live_configured(),
        "writes_enabled": False,          # replay never writes; live path is read-only for now
        "approvals_enabled": False,       # approvals are shown read-only, never executed
        "api_version": config.SRE_API_VERSION,
        "note": "Guided replay — deterministic, simulated investigations. No live "
                "Azure calls, no actions taken.",
    }


@app.get("/api/scenarios")
async def api_scenarios():
    return {"mode": _mode(), "scenarios": scenarios.list_scenarios()}


@app.get("/api/scenarios/{scenario_id}")
async def api_scenario(scenario_id: str):
    s = scenarios.get_scenario(scenario_id)
    if s is None:
        return JSONResponse({"error": "scenario not found"}, status_code=404)
    return s


@app.get("/api/context")
async def api_context():
    """Capabilities + WAF framing + doc links for the explainer panels."""
    return {
        "capabilities": scenarios.CAPABILITIES,
        "waf": scenarios.WAF_NOTES,
        "docs": scenarios.DOCS,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", str(config.PORT))))
