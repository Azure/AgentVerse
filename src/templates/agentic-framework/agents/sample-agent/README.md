# `sample-agent` — agent card (worked reference)

> A copyable reference agent showing the folder convention. Copy this folder, rename it, and
> replace the contents. This card is the template for **every agent's README**.

| | |
|---|---|
| **Name** | `sample-agent` |
| **Purpose** | {{One sentence: what this agent does.}} |
| **Model** | {{gpt-4.1}} (via APIM gateway) |
| **Input** | `SampleInput` (see `schemas.py`) |
| **Output** | `SampleOutput` (see `schemas.py`) — strict JSON |
| **Tools** | {{none | tool-name (function/mcp/hosted)}} |
| **Orchestration role** | {{e.g. first step in a sequential workflow}} |
| **Failure modes** | {{what happens on malformed output / tool failure, and the fallback}} |

## Files

```
sample-agent/
├── agent.yaml         # declarative spec (from ../../agent-spec/)
├── instructions.md    # versioned system prompt
├── schemas.py         # SampleInput / SampleOutput
├── agent.py           # the MAF Executor (sketch in ../../README.md)
├── tools.py           # function tools, if any
├── evals/             # golden cases (≥3, incl. one adversarial)
└── README.md          # this card
```

## How to use it

1. `cp -r sample-agent agents/<your-agent>` (PowerShell: `Copy-Item -Recurse`).
2. Fill `agent.yaml`, `instructions.md`, `schemas.py` (the contract).
3. Implement `agent.py`; import the client from `../shared/azure_client.py`.
4. Add tools, guardrails, evals; then run the [checklist](../../CHECKLIST.md).

> The three spec files here are copies of [`../../agent-spec/`](../../agent-spec/). Keep the
> field names in `schemas.py` and the JSON block in `instructions.md` in sync.
