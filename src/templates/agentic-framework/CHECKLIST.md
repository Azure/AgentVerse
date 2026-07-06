# Production-Readiness Checklist

> Run this before calling an agent (or a demo) done. It's the ship gate. If a box can't be
> ticked, you have a to-do, not a finished agent.

## Per-agent

**Contract & prompt**
- [ ] Agent is declared in `agent.yaml` (name, model, tools, protocol).
- [ ] Instructions live in a versioned `instructions.md`, not inline strings.
- [ ] Output is a strict, typed schema (Pydantic) — no free-form prose the next step must guess at.
- [ ] The smallest model that passes evals is used (not the biggest by default).

**Tools**
- [ ] Every tool has a precise name, description, and typed parameters.
- [ ] Tool failures are handled (fallback or explicit error), not swallowed.
- [ ] External tools (MCP/hosted) have a timeout and a retry policy.

**Guardrails**
- [ ] Untrusted input is validated before it reaches the model.
- [ ] Prompt-injection defense is stated in the instructions and tested with a hostile case.
- [ ] Model output is validated against its schema before use.
- [ ] Content safety is enforced (via the APIM gateway).

**Model access**
- [ ] All model calls go through the APIM gateway — no API keys in code or `.env` committed.
- [ ] Auth uses `DefaultAzureCredential` (managed identity in cloud, `az login` locally).

**Observability**
- [ ] Traces are emitted for the agent and each tool call.
- [ ] Token/cost metrics are emitted and correlated by a run id.

**Evaluation**
- [ ] At least 3 golden cases exist, including one adversarial/edge case.
- [ ] Evals assert the decision/output, not just "it ran."
- [ ] Evals run in CI and block merge on regression.

**Cost & latency**
- [ ] A token limit is set per agent.
- [ ] Reasoning effort / model size is tuned to the latency budget.

## Per-demo (in addition)

- [ ] Human-in-the-loop is present for any costly or irreversible action.
- [ ] `agentverse.yaml` is filled in and validates against the catalog schema.
- [ ] `.env.example` lists every variable; no secrets committed.
- [ ] `README.md` has scenario, architecture diagram, quick start, troubleshooting.
- [ ] `.github/` governance (CODEOWNERS, PR template, eval workflow) points at real teams/paths.
- [ ] The demo runs after being cloned on its own (no repo-root dependency).
- [ ] Falls back gracefully (mocks) when Azure endpoints are absent, if feasible.
