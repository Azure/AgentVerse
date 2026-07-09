# `fixtures/` — recorded agent responses for replay mode

When no `PROJECT_ENDPOINT` is configured (or `REPLAY_MODE=true`), the shared
Foundry runner serves these instead of calling Azure — the demo runs with zero
cloud dependencies. One file per `(agent, fixture_key)`; the key is the
disruption id.

These are the agent's **raw** outputs: the deterministic policy gate in each
agent's `agent.py` still runs on top of them, exactly as in live mode.

The current files are hand-authored to realistic values. Re-record them from a
real run with `scripts/run_demo.py --record` once an Azure endpoint is available.
