# `backend/` — the plant, the control loop, and (next) the API

## What's here today

```
backend/
├── plant_data.json    # the mock plant: 5 machines, 8 orders, materials, changeover matrix
├── plant.py           # plant state + the deterministic feasibility checker & dispatcher
├── disruptions.py     # 4 scripted raw events + constraint-monitor classification (code)
├── pipeline.py        # the control loop: Sense -> Simulate -> Decide -> Act (event generator)
├── kpis.py            # dashboard numbers: idle hours, adherence %, schedule version
└── main.py            # FastAPI: /api/state · /api/run/{key} (SSE) · /api/choose · /api/reset
                       #   + serves ../frontend (same-origin, no CORS needed)
```

- **`plant.py`** is the "hard constraints are never enforced by the LLM alone"
  guarantee: `validate_moves()` checks tool compatibility, downtime windows,
  material ETAs, and machine overlaps; `apply_scenario()` re-validates
  immediately before publishing (the last line of defense).
- **`pipeline.py`** yields plain-dict events (`agent_start`, `agent_log`,
  `agent_done`, `escalation`, `decision`, `schedule_updated`, `done`) consumed
  identically by the CLI runner ([`../scripts/run_demo.py`](../scripts/run_demo.py)),
  the eval gate, and — next — the SSE endpoint.

## Run the loop without any UI

```bash
python scripts/run_demo.py --disruption machine_down          # autonomy
python scripts/run_demo.py --disruption material_delay --choose SCN-A   # HITL
python scripts/run_demo.py --disruption prompt_injection      # guardrail
```

## Run the dashboard

```bash
python -m uvicorn backend.main:app --port 8000    # open http://localhost:8000
```

`GET /api/run/{key}` streams the pipeline over Server-Sent Events; in replay
mode events are paced by `REPLAY_EVENT_DELAY` (default 0.8 s) so the audience
can watch the agents think. An `escalation` event parks the scored scenarios
server-side until the planner answers via `POST /api/choose`. State is one
plant per process — it's a demo, not a multi-tenant app; `POST /api/reset`
starts over.
