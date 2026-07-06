# `agents/` — per-agent folder convention

> Blocks #1–#4. Every agent gets its own folder; shared plumbing lives in `shared/`.

## Convention

```
agents/
├── shared/                    # plumbing every agent reuses (block #2 & #4)
│   ├── azure_client.py        # the ONE model/agent client — points at the APIM gateway
│   ├── guardrails.py          # input/output validation helpers (block #6)
│   ├── telemetry.py           # OpenTelemetry setup + token metrics (block #7)
│   ├── memory.py              # long-term store access (block #4)
│   └── models.py              # cross-agent shared enums/dataclasses
├── <agent-name>/              # one folder per agent
│   ├── agent.yaml             # the declarative spec (block #1) — see ../agent-spec/
│   ├── instructions.md        # versioned system prompt (block #1)
│   ├── schemas.py             # typed I/O contract (block #1)
│   ├── agent.py               # the Executor implementation (MAF)
│   ├── tools.py               # this agent's function tools (block #3), if any
│   ├── evals/                 # this agent's golden cases (block #8)
│   └── README.md              # the agent card: what it does, its I/O, its tools
└── sample-agent/              # a worked reference you can copy
```

## Rules

- **One agent, one folder.** No shared prompt files between agents; copy and diverge.
- **Spec is data.** `agent.yaml` + `instructions.md` + `schemas.py` hold the contract; keep
  it out of `agent.py`.
- **Client comes from `shared/`.** Never construct a model client inline — import it from
  `shared/azure_client.py` so every call goes through the gateway with managed identity.
- **Every agent has a README (its "agent card").** One screen: purpose, inputs, outputs,
  tools, failure modes.

## Build order for a new agent

1. Copy [`../agent-spec/`](../agent-spec/) into `agents/<name>/` and fill `agent.yaml`,
   `instructions.md`, `schemas.py`.
2. Implement `agent.py` (an `Executor` wrapping the client from `shared/`).
3. Add tools in `tools.py` if needed ([`../tools/`](../tools/)).
4. Add guardrails at the boundaries ([`../guardrails/`](../guardrails/)).
5. Add `evals/` cases ([`../evals/`](../evals/)).
6. Write the agent card `README.md`.
7. Run the [checklist](../CHECKLIST.md).
