# Agentic AI Framework — the AgentVerse blueprint

> The **standard, best-practice way to build the agents inside an AgentVerse demo.**
> Opinionated for **Microsoft Agent Framework (MAF)** + **Azure AI Foundry**, with the
> vendor-neutral principles stated so the ideas travel.
>
> 🇬🇧 English · 🇪🇸 [Español](#-en-español)

---

If you are brand new, read the [hub getting-started guide](../README.md) first. This
document is the deeper reference: the **principles**, the **8 building blocks** of an agent,
and pointers into each subsystem folder.

## Table of contents

- [First principles](#first-principles)
- [Anatomy of an agent](#anatomy-of-an-agent)
- [The 8 building blocks](#the-8-building-blocks)
- [How the folders map to the blocks](#how-the-folders-map-to-the-blocks)
- [Minimal end-to-end example](#minimal-end-to-end-example)
- [En español](#-en-español)

---

## First principles

These hold regardless of framework. Everything else follows from them.

1. **Start simple. Earn complexity.** A single well-prompted LLM call beats a multi-agent
   system you can't debug. Add agents/tools/orchestration only when a *measured* limitation
   forces it. (Anthropic, *Building Effective Agents*.)
2. **Prefer workflows over free-roaming agents when the steps are known.** A fixed
   sequential/parallel workflow is predictable and cheap. Reserve open-ended agent loops for
   genuinely open-ended problems.
3. **Make agents declarative.** An agent = *model + versioned instructions + typed tools +
   typed I/O*. Keep that contract in data (`agent.yaml` + `instructions.md`), not scattered
   in code.
4. **Every model call goes through a gateway.** Route through Azure APIM with managed
   identity: no secrets in code, plus central rate limits, content safety, and audit.
5. **Treat untrusted input as hostile.** Validate inputs and outputs. Defend against prompt
   injection explicitly (see [`guardrails/`](guardrails/)).
6. **Observability from line one.** If you can't see the tokens, latency, and tool calls of
   a run, you can't operate it. Emit traces and metrics from the start.
7. **Evals gate change.** A prompt tweak is a code change. Prove it with a golden dataset
   before it ships (see [`evals/`](evals/)).
8. **Humans own high-stakes decisions.** Add human-in-the-loop where a wrong action is
   expensive or irreversible.
9. **Budget cost and latency.** Reasoning models add seconds and tokens per step. Pick the
   smallest model that passes evals; set token limits.

---

## Anatomy of an agent

```
                    ┌────────────────────────────────────────────┐
   user / upstream  │                  AGENT                      │
   ─────────────►   │                                             │
                    │   instructions (versioned prompt)           │
                    │   + model  (via APIM gateway)               │──► model call
                    │   + tools  (function / MCP / hosted)        │──► tool calls
                    │   + memory (thread + long-term)             │
                    │   + guardrails (in / out)                   │
                    │                                             │
                    └───────────────┬─────────────────────────────┘
                                    │ typed output (Pydantic)
                                    ▼
                         orchestration (next agent / done)
              (traces + token metrics emitted throughout; evals score it)
```

---

## The 8 building blocks

Build every agent out of these. Each links to the folder that shows the AgentVerse way.

### 1. Agent spec — the declarative contract → [`agent-spec/`](agent-spec/)
An agent is defined by data: `agent.yaml` (name, model, tool list, protocol) +
`instructions.md` (the versioned system prompt) + `schemas.py` (typed input/output). This
mirrors Foundry's own `agent.yaml` manifest, so a local agent and a hosted Foundry agent
share one shape.

### 2. Model access — always via the gateway → [`agents/shared/`](agents/shared/)
Get the model client from a single `shared/azure_client.py` that points at **APIM**, authed
with `DefaultAzureCredential` (managed identity in the cloud, `az login` locally). No demo
holds API keys. The gateway enforces token limits and content safety centrally.

### 3. Tools — how the agent touches the world → [`tools/`](tools/)
Three kinds: **function tools** (a typed Python function), **MCP servers** (external tools
over the Model Context Protocol), and **hosted tools** (Foundry-managed, e.g. Bing
Grounding). Every tool has a precise name, description, and typed parameters — the model
only uses tools it understands.

### 4. Memory & state → [`agents/shared/`](agents/shared/)
Short-term = the conversation **thread** passed between executors. Long-term = an explicit
store (Cosmos DB in the insurance demo) written through a repository. Keep memory explicit;
never rely on the model to "remember."

### 5. Orchestration — how agents combine → [`orchestration/`](orchestration/) · [`PATTERNS.md`](PATTERNS.md)
Pick a pattern deliberately: single-agent, sequential, routing, parallel,
orchestrator-workers, evaluator-optimizer, group-chat/handoff, human-in-the-loop. Each maps
to MAF `WorkflowBuilder` / `Executor` primitives. `PATTERNS.md` gives *what / when / when
not / MAF construct / diagram* for each.

### 6. Guardrails — the safety net → [`guardrails/`](guardrails/)
Input validation, output-schema validation, content safety (via the gateway), and explicit
**prompt-injection defense** in the instructions. Generalized from the insurance intake
agent, which flags manipulation attempts as high-severity.

### 7. Observability → [`observability/`](observability/)
OpenTelemetry traces for every agent and tool call, plus token/cost metrics emitted to
Application Insights (the APIM policy `emit-token-metric` does this centrally). Correlate by
a run/claim id.

### 8. Evaluation → [`evals/`](evals/)
A golden dataset of input→expected cases, run by a harness that asserts decisions and writes
a report. Wire it into CI as an **eval gate** so a regression blocks the PR.

---

## How the folders map to the blocks

| Folder | Blocks it covers |
|---|---|
| [`agent-spec/`](agent-spec/) | 1 (contract) |
| [`agents/`](agents/) | 1–4 (a full agent + shared model/memory/guardrail utilities) |
| [`orchestration/`](orchestration/) | 5 (patterns as runnable skeletons) |
| [`tools/`](tools/) | 3 (function / MCP / hosted) |
| [`guardrails/`](guardrails/) | 6 |
| [`observability/`](observability/) | 7 |
| [`evals/`](evals/) | 8 |
| [`PATTERNS.md`](PATTERNS.md) | 5 (decision guide) |
| [`CHECKLIST.md`](CHECKLIST.md) | all — the ship gate |

---

## Minimal end-to-end example

The smallest useful agent, in the AgentVerse shape (MAF). This is a *reference sketch* —
the real, copyable skeletons live in [`agents/sample-agent/`](agents/sample-agent/).

```python
# agents/sample_agent/agent.py  (sketch)
from agent_framework import ChatMessage, Executor, Role, WorkflowContext, handler
from agent_framework.azure import AzureAIAgentClient

from agents.shared.azure_client import get_agent_client   # block 2: gateway
from agents.sample_agent.schemas import SampleOutput        # block 1: typed I/O
from agents.shared.guardrails import guard_input            # block 6: guardrails


class SampleExecutor(Executor):
    """Wraps a persistent Foundry prompt agent (created from agent.yaml)."""

    @handler
    async def handle(self, msg: ChatMessage, ctx: WorkflowContext[SampleOutput]) -> None:
        guard_input(msg.text)                                # validate untrusted input
        agent = get_agent_client("sample-agent")             # via APIM + managed identity
        resp = await agent.run(msg)                          # traced automatically (block 7)
        output = SampleOutput.model_validate_json(resp.text) # enforce output schema
        await ctx.send_message(output)
```

From here, orchestration decides what happens next; evals prove it still behaves. Read the
[production-readiness checklist](CHECKLIST.md) before calling it done.

---
---

## 🇪🇸 En español

> La **forma estándar y recomendada de construir los agentes** dentro de un demo de
> AgentVerse. Opinionada para **Microsoft Agent Framework (MAF)** + **Azure AI Foundry**,
> con los principios neutrales enunciados para que las ideas viajen.

Si eres nuevo, lee primero la [guía de inicio del hub](../README.md).

### Primeros principios

1. **Empieza simple. Gánate la complejidad.** Una sola llamada LLM bien diseñada supera a un
   sistema multi-agente que no puedes depurar. Añade agentes/herramientas/orquestación solo
   cuando una limitación *medida* lo exija.
2. **Prefiere flujos de trabajo a agentes libres cuando los pasos se conocen.** Un flujo
   secuencial/paralelo fijo es predecible y barato. Reserva los bucles de agente abiertos
   para problemas realmente abiertos.
3. **Haz los agentes declarativos.** Agente = *modelo + instrucciones versionadas +
   herramientas tipadas + E/S tipada*. Mantén ese contrato en datos (`agent.yaml` +
   `instructions.md`), no disperso en el código.
4. **Toda llamada al modelo pasa por un gateway.** Enruta por Azure APIM con identidad
   administrada: sin secretos en código, más límites de tokens, content safety y auditoría.
5. **Trata la entrada no confiable como hostil.** Valida entradas y salidas. Defiéndete de la
   inyección de prompts explícitamente (ver [`guardrails/`](guardrails/)).
6. **Observabilidad desde la primera línea.** Emite trazas y métricas desde el inicio.
7. **Los evals controlan el cambio.** Un ajuste de prompt es un cambio de código: pruébalo
   con un dataset dorado antes de publicarlo (ver [`evals/`](evals/)).
8. **Las personas deciden lo crítico.** Añade human-in-the-loop donde un error sea caro o
   irreversible.
9. **Presupuesta coste y latencia.** Elige el modelo más pequeño que pase los evals; pon
   límites de tokens.

### Los 8 bloques de construcción

1. **Spec del agente** — contrato declarativo → [`agent-spec/`](agent-spec/)
2. **Acceso al modelo** — siempre vía gateway → [`agents/shared/`](agents/shared/)
3. **Herramientas** — función / MCP / hosted → [`tools/`](tools/)
4. **Memoria y estado** — thread + almacén de largo plazo → [`agents/shared/`](agents/shared/)
5. **Orquestación** — elige patrón → [`orchestration/`](orchestration/) · [`PATTERNS.md`](PATTERNS.md)
6. **Guardrails** — validación E/S, content safety, anti-inyección → [`guardrails/`](guardrails/)
7. **Observabilidad** — trazas OTel + métricas de tokens → [`observability/`](observability/)
8. **Evaluación** — dataset dorado + eval gate → [`evals/`](evals/)

Antes de dar un agente por terminado, pasa el [checklist de producción](CHECKLIST.md).
