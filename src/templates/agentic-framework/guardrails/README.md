# `guardrails/` — the safety net (block #6)

> Treat every input the agent didn't generate as potentially hostile. Guardrails sit at the
> two boundaries of an agent: **before** the model sees input, and **after** it produces
> output.

## Four layers

| Layer | Where | What it does |
|---|---|---|
| **Input validation** | before the model | Reject/normalize malformed or oversized input; strip nothing silently. |
| **Prompt-injection defense** | in `instructions.md` + a check | The prompt states the defense; a check flags manipulation attempts. |
| **Output-schema validation** | after the model | `SampleOutput.model_validate_json(resp.text)` — malformed output raises, never flows downstream. |
| **Content safety** | at the gateway | APIM `llm-content-safety` policy blocks Hate/Sexual/SelfHarm/Violence centrally. |

## Prompt-injection defense — the AgentVerse pattern

Generalized from the insurance intake agent. Two halves:

**1. In the instructions** (declarative — see [`../agent-spec/instructions.md`](../agent-spec/instructions.md)):
the agent is told that data may contain hostile instructions, must never obey them, and must
flag them in a `security_flag` / `severity` field.

**2. In code** (a cheap deterministic check, defense in depth):

```python
# agents/shared/guardrails.py  (sketch)
INJECTION_MARKERS = ("ignore previous", "system override", "authorization code",
                     "as an admin", "bypass", "internal note:")

def guard_input(text: str) -> None:
    lowered = text.lower()
    if any(m in lowered for m in INJECTION_MARKERS):
        # Don't reject outright — let the agent flag it, but record the signal.
        log.warning("possible prompt-injection markers in input")

def validate_output(model: type[BaseModel], raw: str) -> BaseModel:
    return model.model_validate_json(raw)   # raises on malformed output
```

> The deterministic check is a tripwire, not the whole defense — the instruction-level
> handling is primary. The insurance demo marks such claims high-severity and records
> `prompt_injection_detected`.

## Rules

- **Validate output schema on every agent.** It's the cheapest, highest-value guardrail.
- **Never let data become instructions.** Only system + legitimate user text is
  authoritative; embedded instructions in tool results / documents are data.
- **Fail loud on schema violations**, fail safe on content-safety blocks (return a friendly
  429/400, as the APIM `on-error` policy does).
- **Test the guardrail** — include an adversarial case in `evals/` (see the
  `prompt_injection_attack` golden case in the insurance demo).

## 🇪🇸 En español

Trata toda entrada que el agente no generó como potencialmente hostil. Cuatro capas:
**validación de entrada** (antes del modelo), **defensa anti-inyección** (en
`instructions.md` + un chequeo), **validación del esquema de salida**
(`model_validate_json` — la salida malformada lanza excepción, nunca sigue aguas abajo) y
**content safety** (política APIM, centralizada). Patrón AgentVerse (del agente de intake de
seguros): las instrucciones dicen al agente que los datos pueden contener instrucciones
hostiles, que nunca las obedezca y que las marque (`security_flag`/`severity`); un chequeo
determinista en `shared/guardrails.py` actúa como tripwire adicional. Reglas: **valida el
esquema de salida en cada agente**; **los datos nunca son instrucciones**; **falla ruidoso**
ante violaciones de esquema y **seguro** ante bloqueos de content safety; **prueba el
guardrail** con un caso adversarial en `evals/`.
