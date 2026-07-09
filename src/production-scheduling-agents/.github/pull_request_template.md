<!-- PR template for Production Scheduling AI Agents. Keep it short; check the boxes that apply. -->

## What & why

<!-- One or two sentences: what changes and the reason. -->

## Type of change

- [ ] New agent / capability
- [ ] Prompt or schema change (agent contract)
- [ ] Orchestration change
- [ ] Infra / deploy
- [ ] Docs / branding
- [ ] Fix

## Agent contract

- [ ] `instructions.md` and `schemas.py` updated together (if the contract changed)
- [ ] Output remains a strict, typed schema

## Safety & quality gates

- [ ] Guardrails cover any new untrusted input
- [ ] Golden `evals/` cases added/updated; suite passes locally
- [ ] Observability (tracing/metrics) intact
- [ ] `agentverse.yaml` updated if agents/models/capabilities changed
- [ ] Ran the [checklist](../../templates/agentic-framework/CHECKLIST.md)

## Reviewers

<!-- The CODEOWNER for the touched domain must approve. The eval gate must be green. -->
