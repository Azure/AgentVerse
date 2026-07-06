# `observability/` — see what your agents do (block #7)

> If you can't see the tokens, latency, and tool calls of a run, you can't operate or debug
> it. Turn this on from line one, not after something breaks.

## What to emit

| Signal | How | Why |
|---|---|---|
| **Traces** | OpenTelemetry spans per agent + per tool call | Reconstruct exactly what happened in a run. |
| **Token / cost metrics** | APIM `azure-openai-emit-token-metric` policy → Application Insights | Track spend per agent/model/run; catch runaway costs. |
| **Correlation id** | A run/claim id on every span & log | Tie the whole multi-agent run together. |
| **Domain events** | `agent_start` / `agent_log` / `agent_done` streamed to the UI | Live progress for the demo audience. |

## Setup — sketch

```python
# agents/shared/telemetry.py  (sketch)
from opentelemetry import trace
from azure.monitor.opentelemetry import configure_azure_monitor

def setup_telemetry(service_name: str) -> None:
    """Call once at startup. Reads APPLICATIONINSIGHTS_CONNECTION_STRING."""
    configure_azure_monitor(service_name=service_name)

tracer = trace.get_tracer("agentverse")

# In an executor:
#   with tracer.start_as_current_span("sample-agent.run") as span:
#       span.set_attribute("run_id", run_id)
#       ...
```

## Two layers work together

- **App-level:** OpenTelemetry spans you create around agents and tools (the code above).
- **Gateway-level:** APIM emits token metrics and traces for *every* model call
  automatically, with dimensions `Agent`, `Model`, and a claim/run id — no app code needed.
  This is why all model calls must go through the gateway (block #2).

## Rules

- **One correlation id per run**, set on the first span and propagated everywhere.
- **Emit metrics centrally at the gateway** so you can't forget to instrument a call.
- **Don't log secrets or full PII** — log ids and shapes, not raw payloads.

## 🇪🇸 En español

Si no puedes ver los tokens, la latencia y las llamadas a herramientas de una ejecución, no
puedes operarla ni depurarla. Emite: **trazas** (spans OpenTelemetry por agente y por
herramienta), **métricas de tokens/coste** (política APIM `emit-token-metric` →
Application Insights), un **id de correlación** por ejecución en cada span/log, y **eventos
de dominio** (`agent_start`/`agent_log`/`agent_done`) a la UI. Dos capas: a nivel de app
(spans que creas en `shared/telemetry.py`) y a nivel de gateway (APIM instrumenta cada
llamada al modelo automáticamente — por eso todas pasan por el gateway). Reglas: **un id de
correlación por ejecución**; **emite métricas en el gateway** para no olvidar instrumentar;
**no registres secretos ni PII completa** (ids y formas, no payloads crudos).
