"""Model Evaluator — FastAPI (single container: UI at / + JSON/SSE API).

Compares two Foundry-deployed chat models on one prompt, in parallel, reporting
latency, TTFT, tokens and (optionally) a blind LLM judge verdict.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import azure_clients, config, discovery, guardrails, inference, judge

log = logging.getLogger("model-evaluator")
app = FastAPI(title="Model Evaluator")

FRONTEND_PATH = Path(__file__).resolve().parent.parent / "frontend"


def _setup_observability() -> None:
    conn = config.APPLICATIONINSIGHTS_CONNECTION_STRING
    if not conn:
        return
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        configure_azure_monitor(connection_string=conn)
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        FastAPIInstrumentor.instrument_app(app)
        HTTPXClientInstrumentor().instrument()
        log.info("Azure Monitor tracing enabled")
    except Exception as exc:  # noqa: BLE001
        log.warning("observability setup failed: %s", exc)


_setup_observability()
app.mount("/static", StaticFiles(directory=str(FRONTEND_PATH)), name="static")

_SSE_HEADERS = {"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# --- static -----------------------------------------------------------------

@app.get("/")
async def root():
    return FileResponse(FRONTEND_PATH / "index.html")


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "inference": config.has_inference(),
            "project_endpoint": bool(config.PROJECT_ENDPOINT)}


# --- discovery --------------------------------------------------------------

@app.get("/api/models")
async def api_models(refresh: int = 0):
    do_refresh = bool(refresh) and guardrails.allow_refresh()
    try:
        snap = await discovery.get_models(refresh=do_refresh)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"models": [], "source": "error",
                             "error": f"{type(exc).__name__}: {exc}"}, status_code=200)
    snap["inference_enabled"] = config.has_inference()
    snap["limits"] = {
        "max_output_tokens": config.MAX_OUTPUT_TOKENS,
        "max_prompt_chars": config.MAX_PROMPT_CHARS,
        "max_models_per_run": config.MAX_MODELS_PER_RUN,
    }
    return snap


# --- request validation -----------------------------------------------------

def _validate(body: Dict[str, Any]) -> tuple[list, str, str, dict] | JSONResponse:
    if not config.has_inference():
        return JSONResponse({"error": "inference not configured (AZURE_OPENAI_ENDPOINT unset)"}, status_code=503)
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        return JSONResponse({"error": "prompt is required"}, status_code=400)
    if len(prompt) > config.MAX_PROMPT_CHARS:
        return JSONResponse({"error": f"prompt too long (>{config.MAX_PROMPT_CHARS} chars)"}, status_code=400)
    # Coarse token guard (~4 chars/token) without a tokenizer dependency.
    if len(prompt) / 4 > config.MAX_PROMPT_TOKENS:
        return JSONResponse({"error": f"prompt too long (~>{config.MAX_PROMPT_TOKENS} tokens)"}, status_code=400)

    names = body.get("models") or []
    if not isinstance(names, list) or not (1 < len(names) <= config.MAX_MODELS_PER_RUN):
        return JSONResponse({"error": f"select exactly {config.MAX_MODELS_PER_RUN} models"}, status_code=400)
    if len(set(names)) != len(names):
        return JSONResponse({"error": "pick two different deployments"}, status_code=400)

    # Validate every name against the server-discovered, selectable set.
    metas = []
    for n in names:
        m = discovery.find(n)
        if m is None or not m.get("selectable"):
            return JSONResponse({"error": f"model not available/selectable: {n}"}, status_code=400)
        metas.append(m)

    system = (body.get("system") or "").strip()
    params = {
        "temperature": body.get("temperature"),
        "top_p": body.get("top_p"),
        "max_tokens": body.get("max_tokens") or config.MAX_OUTPUT_TOKENS,
        "seed": body.get("seed"),
    }
    return metas, prompt, system, params


# --- compare (SSE via streaming fetch on the client) ------------------------

@app.post("/api/compare")
async def api_compare(request: Request):
    if not guardrails.check_rate_limit(_client_ip(request)):
        return JSONResponse({"error": "rate limit exceeded, slow down"}, status_code=429)
    body = await request.json()
    validated = _validate(body)
    if isinstance(validated, JSONResponse):
        return validated
    metas, prompt, system, params = validated

    async def gen():
        slot = guardrails.SSESlot()
        async with slot:
            if not slot.acquired:
                yield _sse("error", {"message": "too many concurrent runs, try again shortly"})
                return
            yield _sse("start", {"models": [m["name"] for m in metas]})
            try:
                results = await inference.compare(
                    metas, prompt, system,
                    params["temperature"], params["top_p"], params["max_tokens"], params["seed"])
            except Exception as exc:  # noqa: BLE001
                yield _sse("error", {"message": f"{type(exc).__name__}: {exc}"})
                return
            for r in results:
                yield _sse("result", r)
            yield _sse("done", {"count": len(results)})

    return StreamingResponse(gen(), media_type="text/event-stream", headers=_SSE_HEADERS)


# --- judge (explicit) -------------------------------------------------------

@app.post("/api/judge")
async def api_judge(request: Request):
    if not guardrails.check_rate_limit(_client_ip(request)):
        return JSONResponse({"error": "rate limit exceeded, slow down"}, status_code=429)
    body = await request.json()
    prompt = (body.get("prompt") or "").strip()
    a = body.get("a") or {}
    b = body.get("b") or {}
    if not prompt or not a.get("text") or not b.get("text"):
        return JSONResponse({"error": "prompt and both non-empty answers are required"}, status_code=400)
    verdict = await judge.judge(prompt, a["text"], b["text"],
                                a.get("name", "A"), b.get("name", "B"))
    status = 200 if "error" not in verdict else 502
    return JSONResponse(verdict, status_code=status)


def _sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.on_event("shutdown")
async def _shutdown():
    await azure_clients.aclose()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8770")))
