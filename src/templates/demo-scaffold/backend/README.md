# `backend/` — API + streaming

FastAPI backend that runs the workflow and streams progress to the frontend.

## Convention

```
backend/
├── main.py            # FastAPI app: routes + CORS + startup (telemetry, clients)
├── stream.py          # SSE or WebSocket helper to push agent events to the UI
└── requirements.txt   # (or use the demo-root requirements.txt)
```

## What it does

- Exposes an endpoint (e.g. `GET /api/run` for SSE, or a WebSocket) that triggers the
  workflow from [`../agents/`](../agents/) and streams events as they happen.
- Emits domain events the UI renders: `agent_start`, `agent_log`, `agent_done`, plus your
  demo's payloads and a final `done`.
- Sets up observability at startup (see
  [`../../templates/agentic-framework/observability/`](../../templates/agentic-framework/observability/)).

## Sketch

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.get("/api/run")
async def run():
    async def events():
        async for ev in run_workflow():      # from ../agents/
            yield sse(ev)                     # format as Server-Sent Event
    return StreamingResponse(events(), media_type="text/event-stream")
```

## Rules

- **Stream, don't block.** The demo's value is watching agents work in real time.
- **Start telemetry once, at startup.**
- **Config from env** (`.env` / container settings) — never hardcode endpoints or keys.
