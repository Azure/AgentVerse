# `frontend/` — the UI

Where a human watches the agents work. Pick the lightest option that sells the demo.

## Two options

| Option | Use when | Reference demo |
|---|---|---|
| **Vanilla HTML/JS** | Simple, single-page, few moving parts | foundryairlines |
| **React + Vite + Tailwind** | Rich dashboard, multiple views, roles | insurance |

## Convention (vanilla)

```
frontend/
├── index.html         # the page; connects to the backend stream (SSE/WebSocket)
├── app.js             # subscribes to events, renders agent progress
└── styles.css
```

## Convention (React)

```
frontend/
├── src/
│   ├── main.tsx
│   ├── api.ts         # backend calls + stream subscription
│   ├── brand.ts       # single source of brand strings/assets (see ../BRANDING.md)
│   └── components/
├── public/            # brand-logo.png, favicon
├── package.json
└── vite.config.ts
```

## Rules

- **Render the stream live** — show `agent_start` / `agent_log` / `agent_done` as they
  arrive, so the audience sees the agents thinking.
- **Point at the backend via config** (an env/base-URL), not a hardcoded host.
- If whitelabel, keep all brand strings/assets in one place ([`../BRANDING.md`](../BRANDING.md)).

> No UI? Set `frontend: none` in `agentverse.yaml` and delete this folder.
