# `agents/` — the agents in this demo

Build these following the AgentVerse blueprint:
**[`../../templates/agentic-framework/`](../../templates/agentic-framework/)**.

## Convention (see the blueprint for detail)

```
agents/
├── shared/              # azure_client (gateway), guardrails, telemetry, memory, models
└── <agent-name>/        # agent.yaml · instructions.md · schemas.py · agent.py · tools.py · evals/ · README.md
```

## To add an agent

1. Copy [`../../templates/agentic-framework/agent-spec/`](../../templates/agentic-framework/agent-spec/)
   into `agents/<name>/` and fill the contract (`agent.yaml`, `instructions.md`, `schemas.py`).
2. Implement `agent.py` (a MAF `Executor` using the client from `shared/azure_client.py`).
3. Wire it into the workflow (see the orchestration you chose in
   [`PATTERNS.md`](../../templates/agentic-framework/PATTERNS.md)).
4. Add guardrails, evals, and a per-agent `README.md` (the "agent card").
5. Reflect the new agent in `../agentverse.yaml`.

> Reminder: model access only via `shared/azure_client.py` (gateway + managed identity), and
> every agent returns a typed Pydantic schema.
