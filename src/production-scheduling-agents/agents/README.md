# `agents/` — the agents in this demo

Build these following the AgentVerse blueprint:
**[`../../templates/agentic-framework/`](../../templates/agentic-framework/)**.

## The four roles (two LLM agents + two code roles)

| Role | Status | Job |
|---|---|---|
| [`constraint-monitor/`](constraint-monitor/) | ⚙️ deterministic code | Classify raw feed events against hard/soft constraints and run the injection guardrail — [`backend/disruptions.py`](../backend/disruptions.py). Promotable to an agent when real telemetry lands. |
| [`schedule-orchestrator/`](schedule-orchestrator/) | ✅ LLM agent | Coordinate the workers; decide autonomous adjustment vs. escalation to the human planner (policy gate in code). |
| [`scenario-simulator/`](scenario-simulator/) | ✅ LLM agent | Generate and score alternative schedules; every proposal re-validated by the deterministic feasibility checker. |
| [`schedule-dispatcher/`](schedule-dispatcher/) | ⚙️ deterministic code | Apply the validated scenario and notify work centers — [`backend/plant.py`](../backend/plant.py) `apply_scenario()` + [`backend/pipeline.py`](../backend/pipeline.py). |

The LLM agents sit exactly where judgment lives (trade-off analysis, the
autonomy-vs-escalation call); sensing and acting are deterministic code on
purpose. Each folder keeps its README (the "agent card") describing the contract.

## Convention (see the blueprint for detail)

```
agents/
├── shared/              # foundry.py (agent runner + replay mode), guardrails, models
└── <agent-name>/        # agent.yaml · instructions.md · schemas.py · agent.py · tools.py · evals/ · README.md
```

## To implement an agent

1. Copy [`../../templates/agentic-framework/agent-spec/`](../../templates/agentic-framework/agent-spec/)
   into `agents/<name>/` and fill the contract (`agent.yaml`, `instructions.md`, `schemas.py`)
   following that agent's README below.
2. Implement `agent.py` calling `shared/foundry.py`'s `run_agent()` (Foundry Agent in live
   mode, recorded fixtures in replay mode), plus any deterministic policy gate.
3. Wire it into the **orchestrator–workers** workflow (see
   [`PATTERNS.md`](../../templates/agentic-framework/PATTERNS.md) §5, plus §8 for the
   planner escalation branch).
4. Add guardrails, evals, and update the per-agent `README.md`.
5. Reflect any contract change in `../agentverse.yaml`.

> Reminders specific to this demo:
> - Model access only via `shared/foundry.py` (Foundry Agents + managed identity); every
>   agent returns a typed Pydantic schema.
> - **Hard constraints are never enforced by the LLM alone.** The `solve_schedule` tool
>   (deterministic constraint solver) and an output guardrail validate every candidate
>   schedule; an agent can *propose*, only validated schedules can be *published*.
> - Free-text fields arriving from MES/ERP (e.g. operator comments) are untrusted input —
>   run them through the prompt-injection guardrail before they reach any prompt.
