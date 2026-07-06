# `orchestration/` — wiring agents together (block #5)

> Choose a pattern in [`../PATTERNS.md`](../PATTERNS.md), then implement it here with MAF
> `WorkflowBuilder` / `Executor`. This folder holds one skeleton per pattern.

## The MAF primitives

- **`Executor`** — wraps one agent (or one deterministic step). Has `@handler` methods that
  receive a message and `ctx.send_message(...)` / `ctx.yield_output(...)`.
- **`WorkflowBuilder`** — connects executors with `.add_edge(a, b)` and `.build()`.
- **`WorkflowContext[T]`** — typed channel carrying messages between executors.
- **`run_stream(trigger)`** — runs the workflow and streams events (feed these to your SSE /
  WebSocket backend).

## Sequential (the default) — sketch

```python
from agent_framework import WorkflowBuilder

workflow = (
    WorkflowBuilder(name="{{DemoSequential}}", start_executor=step_a)
        .add_edge(step_a, step_b)
        .add_edge(step_b, step_c)
        .build()
)

async for event in workflow.run_stream(trigger):
    ...  # forward to the backend stream
```

## Suggested skeleton files

Create only the ones your demo uses:

| File | Pattern |
|---|---|
| `sequential.py` | fixed pipeline (start here) |
| `parallel.py` | fan-out / fan-in (aggregator executor) |
| `routing.py` | classifier → specialized edges |
| `orchestrator_workers.py` | planner dispatches workers at runtime |
| `evaluator_optimizer.py` | generate → critique → revise (bounded) |
| `human_in_the_loop.py` | pause for operator approval, then resume |

## Rules

- **Start with `sequential.py`.** Only reach for a richer pattern when a measured need
  appears (see [first principles](../README.md#first-principles)).
- **Bound every loop.** Evaluator-optimizer and group-chat patterns must have a
  max-iterations / max-turns cap.
- **Stream events out.** Emit progress (`agent_start`, `agent_log`, `agent_done`) so the UI
  can show the agents working — both existing demos do this.

## 🇪🇸 En español

Conecta agentes con MAF (`Executor` envuelve un agente; `WorkflowBuilder.add_edge(...)` los
une; `run_stream(trigger)` ejecuta y transmite eventos al backend). Elige el patrón en
[`../PATTERNS.md`](../PATTERNS.md) e impleméntalo aquí (un esqueleto por patrón:
`sequential.py`, `parallel.py`, `routing.py`, `orchestrator_workers.py`,
`evaluator_optimizer.py`, `human_in_the_loop.py`). Reglas: **empieza por `sequential.py`**;
**acota todo bucle** (tope de iteraciones/turnos); **transmite eventos** (`agent_start`,
`agent_log`, `agent_done`) para que la UI muestre a los agentes trabajando.
