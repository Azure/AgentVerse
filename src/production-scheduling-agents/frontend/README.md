# `frontend/` — the planner dashboard

Vanilla HTML/JS (no build step, no Node): the lightest option that sells the
demo, per the AgentVerse scaffold guidance.

```
frontend/
├── index.html     # the page: KPI strip, disruption buttons, Gantt board, agent feed
├── app.js         # subscribes to the SSE stream, renders events, answers escalations
└── styles.css     # dark control-room look; tier-1 gold, moved-order highlight
```

## How it works

- Served by the backend (`backend/main.py` mounts this folder), so the API is
  same-origin — no base-URL config, works identically on localhost and App Service.
- **Run a disruption:** each button opens `EventSource('/api/run/<key>')` and renders
  the pipeline events live — `agent_start/log/done` in the activity feed, `escalation`
  as the amber "Your call, planner" card, `decision` as the outcome card,
  `schedule_updated`/`state` reflow the Gantt (moved orders get a green outline).
- **Answer an escalation:** option buttons POST `/api/choose {scenario_id}`; the board
  reflows with the planner's pick.
- **Reset plant** POSTs `/api/reset` back to schedule v1.

## Run it

```bash
python -m uvicorn backend.main:app --port 8000   # from the demo root
# open http://localhost:8000
```

No UI needed? The same pipeline runs from `scripts/run_demo.py` in the terminal.
