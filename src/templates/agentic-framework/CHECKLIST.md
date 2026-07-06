# Production-Readiness Checklist

> Run this before calling an agent (or a demo) done. It's the ship gate. If a box can't be
> ticked, you have a to-do, not a finished agent.
>
> 🇬🇧 English · 🇪🇸 [Español](#-en-español)

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

---
---

## 🇪🇸 En español

> Pásalo antes de dar por terminado un agente (o un demo). Es la puerta de publicación. Si
> una casilla no se puede marcar, tienes una tarea pendiente, no un agente terminado.

### Por agente

**Contrato y prompt**
- [ ] El agente se declara en `agent.yaml` (nombre, modelo, herramientas, protocolo).
- [ ] Las instrucciones viven en un `instructions.md` versionado, no en strings en línea.
- [ ] La salida es un esquema estricto y tipado (Pydantic).
- [ ] Se usa el modelo más pequeño que pasa los evals (no el mayor por defecto).

**Herramientas**
- [ ] Cada herramienta tiene nombre, descripción y parámetros tipados precisos.
- [ ] Los fallos de herramienta se gestionan (fallback o error explícito).
- [ ] Las herramientas externas (MCP/hosted) tienen timeout y política de reintento.

**Guardrails**
- [ ] La entrada no confiable se valida antes de llegar al modelo.
- [ ] La defensa anti-inyección está en las instrucciones y probada con un caso hostil.
- [ ] La salida del modelo se valida contra su esquema antes de usarla.
- [ ] Content safety está activo (vía el gateway APIM).

**Acceso al modelo**
- [ ] Todas las llamadas pasan por el gateway APIM — sin claves en código o `.env`.
- [ ] La autenticación usa `DefaultAzureCredential`.

**Observabilidad**
- [ ] Se emiten trazas del agente y de cada llamada a herramienta.
- [ ] Se emiten métricas de tokens/coste correlacionadas por un id de ejecución.

**Evaluación**
- [ ] Existen ≥3 casos dorados, incluido uno adversarial/límite.
- [ ] Los evals verifican la decisión/salida, no solo que "se ejecutó".
- [ ] Los evals corren en CI y bloquean el merge ante regresión.

**Coste y latencia**
- [ ] Hay un límite de tokens por agente.
- [ ] El esfuerzo de razonamiento / tamaño de modelo se ajusta al presupuesto de latencia.

### Por demo (además)

- [ ] Human-in-the-loop para cualquier acción costosa o irreversible.
- [ ] `agentverse.yaml` relleno y válido contra el esquema del catálogo.
- [ ] `.env.example` lista todas las variables; sin secretos comprometidos.
- [ ] `README.md` con escenario, diagrama de arquitectura, quick start y troubleshooting.
- [ ] La gobernanza en `.github/` apunta a equipos/paths reales.
- [ ] El demo funciona tras clonarse por sí solo (sin dependencia de la raíz del repo).
- [ ] Degrada con elegancia (mocks) cuando no hay endpoints de Azure, si es viable.
