# AgentVerse Templates · Start Here

> **New here? Read this page top to bottom.** It takes you from zero to your first
> running agent demo, then shows you how to build your own and add it to the AgentVerse
> catalog. No prior AgentVerse knowledge assumed.
>
> 🇬🇧 English first · 🇪🇸 Español debajo (see [En español](#-en-español)).

---

## Table of contents

- [What is this? (the 2-minute mental model)](#what-is-this-the-2-minute-mental-model)
- [What's in this folder](#whats-in-this-folder)
- [Prerequisites](#prerequisites)
- [Beginner's guide, part 1 — run your first demo](#beginners-guide-part-1--run-your-first-demo)
- [Beginner's guide, part 2 — create your own demo](#beginners-guide-part-2--create-your-own-demo)
- [Beginner's guide, part 3 — build your first agent](#beginners-guide-part-3--build-your-first-agent)
- [Beginner's guide, part 4 — add it to the catalog](#beginners-guide-part-4--add-it-to-the-catalog)
- [Copy checklist](#copy-checklist)
- [Glossary](#glossary)
- [Where to go next](#where-to-go-next)
- [En español](#-en-español)

---

## What is this? (the 2-minute mental model)

Read these five sentences before anything else:

- **AgentVerse** is a *catalog* of small, self-contained demo apps. Each demo shows one
  realistic scenario (airline promotions, insurance claims, …) solved with AI **agents**.
- An **agent** is a large language model (LLM) that has been given *instructions*, a set of
  *tools* it can call, and a *goal*. It decides, step by step, how to reach the goal.
- A **demo** wires several agents together with a small backend and a UI so a human can
  watch them work. Every demo lives in its own folder under `src/` and is **fully
  independent** — you can clone one demo on its own and it will run.
- We build agents on **Microsoft Agent Framework (MAF)** for orchestration and **Azure AI
  Foundry** for hosting the models and agents. You don't need to be an expert in either to
  start — this template hands you the patterns.
- This `templates/` folder gives you two things: a **demo scaffold** (the standard shape of
  a demo) and an **agentic-framework blueprint** (the standard, best-practice way to build
  the agents inside it).

If you remember one thing: **copy a template, fill in the `{{PLACEHOLDERS}}`, follow the
checklist.** That's the whole workflow.

---

## What's in this folder

```
src/templates/
├── README.md                  ← you are here (the getting-started hub)
├── catalog/                   ← how a demo registers itself in the AgentVerse catalog
│   ├── README.md
│   ├── agentverse.schema.json ← schema every demo's manifest is validated against
│   └── build_catalog.py       ← aggregates all demos' manifests into one catalog index
├── demo-scaffold/             ← copy this to start a NEW, self-contained demo
│   └── … README, .env.example, agents/, backend/, infra/, evals/, .github/, agentverse.yaml
└── agentic-framework/         ← the blueprint for building the agents INSIDE a demo
    ├── README.md              ← principles + the 8 building blocks of an agent
    ├── PATTERNS.md            ← orchestration patterns: which to pick and when
    ├── CHECKLIST.md           ← production-readiness checklist
    ├── agent-spec/            ← the declarative contract for a single agent
    ├── agents/                ← per-agent folder convention + shared utilities
    ├── orchestration/         ← one skeleton per orchestration pattern
    ├── tools/ · guardrails/ · observability/ · evals/
```

Two templates, two jobs:

| I want to… | Use | Start at |
|---|---|---|
| Start a new demo app | `demo-scaffold/` | [Part 2](#beginners-guide-part-2--create-your-own-demo) |
| Build the agents inside it | `agentic-framework/` | [Part 3](#beginners-guide-part-3--build-your-first-agent) |
| List my demo in the catalog | `catalog/` | [Part 4](#beginners-guide-part-4--add-it-to-the-catalog) |

---

## Prerequisites

Install these once. Version numbers are minimums.

| Tool | Why you need it | Get it |
|---|---|---|
| **Python 3.12+** | Agents and backend run on Python | https://www.python.org/downloads/ |
| **Node 20+** (optional) | Only if your demo has a React dashboard | https://nodejs.org/ |
| **Azure CLI 2.60+** | Log in to Azure, create resources | https://learn.microsoft.com/cli/azure/install-azure-cli |
| **Git** | Clone the repo | https://git-scm.com/downloads |
| **VS Code** (recommended) | Editor with Python + Bicep extensions | https://code.visualstudio.com/ |

You will also need:

- An **Azure subscription** with permission to create resources (Owner, or Contributor +
  User Access Administrator).
- Quota for the models your demo uses (e.g. `gpt-4.1`, a `gpt-5.x` reasoning model, or
  `gpt-image-2`). `eastus2` and `swedencentral` are safe regions today.

> **No Azure yet?** You can still read the code and run the parts that ship with mock data.
> Both existing demos fall back to mocks when no Azure endpoint is configured.

Check your setup:

```bash
python --version      # 3.12+
az --version          # 2.60+
az login              # opens a browser; sign in
```

---

## Beginner's guide, part 1 — run your first demo

The fastest way to understand AgentVerse is to run one of the demos that already exists.
We'll use it as a live, working example before you build anything.

**Step 1 — Clone the repository.**

```bash
git clone <this-repo-url>
cd agentverse/src
```

**Step 2 — Pick a demo to explore.** Two complete demos ship in `src/`:

- [`foundryairlines-demo`](../foundryairlines-demo/) — 3 agents in a **sequential** workflow
  (analyze flights → find events → generate banners). Python + a plain HTML/JS front-end.
  Simplest to read first.
- [`insurance-ai-agents`](../insurance-ai-agents/) — 4 agents, a React dashboard, evals,
  governance, and Azure infra. A fuller, enterprise-grade example.

**Step 3 — Follow that demo's own README.** Each demo is self-contained and has its own
step-by-step "Quick Start". Open `foundryairlines-demo/README.md` and run it. You'll:

1. Create a Python virtual environment and install `requirements.txt`.
2. Copy `.env.example` to `.env` and fill in your Azure endpoints.
3. Bootstrap the agents in Foundry.
4. Start the backend and open the front-end.

**Step 4 — Watch the agents work,** then come back here to build your own. You now have a
mental picture of what a finished demo looks like. That picture is exactly what the
templates below reproduce.

---

## Beginner's guide, part 2 — create your own demo

Now you'll scaffold a brand-new, self-contained demo from `demo-scaffold/`.

**Step 1 — Copy the scaffold into a new demo folder.** Pick a short, kebab-case name.

```bash
# from src/
cp -r templates/demo-scaffold my-first-demo
cd my-first-demo
```

> On Windows PowerShell: `Copy-Item -Recurse templates/demo-scaffold my-first-demo`

**Step 2 — Find every placeholder.** Everything you must fill in is written as
`{{DOUBLE_BRACE}}`. List them:

```bash
grep -rn "{{" .        # every match is something to fill in
```

**Step 3 — Fill them in, following the [copy checklist](#copy-checklist) below.** Work
through the files in this order: `agentverse.yaml` → `README.md` → `.env.example` →
`agents/` → `backend/`.

**Step 4 — Keep it independent.** Do **not** move shared code up to the repo root. A demo
must run after being cloned on its own, so it carries its own `LICENSE`, `.github/`,
`.env.example`, and manifest. This is a hard rule of the AgentVerse catalog.

**Step 5 — Set up your Python environment.**

```bash
python -m venv .venv
. .venv/bin/activate                 # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

You now have the skeleton of a demo. Next you'll put real agents inside it.

---

## Beginner's guide, part 3 — build your first agent

Open [`agentic-framework/README.md`](agentic-framework/README.md) alongside this. It
explains the **8 building blocks** of an agent; here is the shortest path through them.

**Step 1 — Describe the agent declaratively.** Copy `agentic-framework/agent-spec/` into
your demo's `agents/<your-agent>/`. Edit `agent.yaml`: give the agent a name, the model it
uses, and a one-line description of its job.

**Step 2 — Write its instructions.** In `instructions.md`, tell the agent *who it is, what
it must do, and the exact shape of its output*. Keep the output a strict JSON schema — the
existing demos all do this so the next agent can parse it. Version this file; it is the
agent's most important asset.

**Step 3 — Give it tools (optional).** If the agent needs to reach the outside world (query
a database, search the web, call an API), add a tool in `tools.py`. See
[`agentic-framework/tools/`](agentic-framework/tools/) for the three tool types (function,
MCP, hosted) and when to use each.

**Step 4 — Pick an orchestration pattern.** Read
[`agentic-framework/PATTERNS.md`](agentic-framework/PATTERNS.md) and choose how your agents
relate: one agent alone, a sequential chain, a router, a parallel fan-out, an
orchestrator with workers, and so on. Start with the **simplest pattern that works** —
usually a single agent or a short sequential chain.

**Step 5 — Add the safety net.** Before you call this done:

- **Guardrails** — validate untrusted input and the agent's output
  ([`guardrails/`](agentic-framework/guardrails/)).
- **Observability** — turn on tracing and token metrics
  ([`observability/`](agentic-framework/observability/)).
- **Evals** — add a few golden cases so you can prove the agent still works after every
  change ([`evals/`](agentic-framework/evals/)).

**Step 6 — Run the [production-readiness checklist](agentic-framework/CHECKLIST.md).** If
every box is ticked, your agent is demo-ready.

---

## Beginner's guide, part 4 — add it to the catalog

AgentVerse is a *catalog*, so every demo advertises itself with one manifest file.

**Step 1 — Fill in `agentverse.yaml`** at the root of your demo. It records the demo's
name, tagline, the agents it contains, the models and Azure services it uses, its
orchestration pattern, difficulty, and tags. The full field list and an example are in
[`catalog/README.md`](catalog/README.md).

**Step 2 — Validate it against the schema.**

```bash
# from src/
python templates/catalog/build_catalog.py --validate my-first-demo/agentverse.yaml
```

**Step 3 — Rebuild the catalog index.** This scans every demo's manifest and produces a
single catalog file — no hand-maintained list, so it never drifts.

```bash
python templates/catalog/build_catalog.py --write
```

Your demo now appears in the AgentVerse catalog. Done.

---

## Copy checklist

Tick these off after copying `demo-scaffold/`:

- [ ] Renamed the folder to a short, kebab-case demo name.
- [ ] Replaced every `{{PLACEHOLDER}}` (`grep -rn "{{" .` returns nothing).
- [ ] `agentverse.yaml` filled in and validates against the schema.
- [ ] `README.md` describes the scenario, architecture, and quick start.
- [ ] `.env.example` lists every variable your demo reads (no real secrets committed).
- [ ] At least one agent built from `agentic-framework/` with instructions + typed output.
- [ ] Guardrails on any untrusted input.
- [ ] Observability (tracing) enabled.
- [ ] At least 3 golden eval cases.
- [ ] `.github/CODEOWNERS`, PR template, and eval workflow point at real teams/paths.
- [ ] `LICENSE` present (the demo is self-contained).
- [ ] Runs after being cloned on its own — no dependency on repo-root files.

---

## Glossary

| Term | Plain-language meaning |
|---|---|
| **Agent** | An LLM given instructions, tools, and a goal, that acts step by step. |
| **LLM** | Large Language Model — the AI model (e.g. GPT) behind an agent. |
| **MAF** | Microsoft Agent Framework — the library that orchestrates agents (`WorkflowBuilder`, `Executor`). |
| **Azure AI Foundry** | Azure's platform for hosting models and agents. |
| **Tool** | A function an agent can call to do something (query a DB, search the web). |
| **Orchestration** | How multiple agents are wired together (sequential, parallel, …). |
| **Guardrail** | A check that validates input into or output out of an agent. |
| **Eval** | An automated test that scores an agent against known-good cases. |
| **Golden dataset** | The set of known-good cases used by evals. |
| **Observability** | Traces and metrics that show what an agent did and how much it cost. |
| **Manifest** | `agentverse.yaml` — the file describing a demo for the catalog. |
| **Placeholder** | A `{{DOUBLE_BRACE}}` marker you must replace when copying a template. |
| **APIM / gateway** | Azure API Management — the front door all model calls go through. |
| **HITL** | Human-in-the-loop — a person approves a step before it proceeds. |

---

## Where to go next

- Building the agents themselves → [`agentic-framework/README.md`](agentic-framework/README.md)
- Choosing an orchestration pattern → [`agentic-framework/PATTERNS.md`](agentic-framework/PATTERNS.md)
- The catalog manifest format → [`catalog/README.md`](catalog/README.md)
- Worked examples → [`foundryairlines-demo`](../foundryairlines-demo/) (simple) ·
  [`insurance-ai-agents`](../insurance-ai-agents/) (full enterprise)

---
---

## 🇪🇸 En español

> **¿Nuevo por aquí? Lee esta página de arriba abajo.** Te lleva de cero a tu primer demo de
> agentes funcionando, y luego a construir el tuyo y añadirlo al catálogo de AgentVerse. No
> se asume conocimiento previo de AgentVerse.

### ¿Qué es esto? (el modelo mental en 2 minutos)

- **AgentVerse** es un *catálogo* de pequeñas apps de demostración autocontenidas. Cada demo
  muestra un escenario realista (promociones de aerolínea, siniestros de seguros, …)
  resuelto con **agentes** de IA.
- Un **agente** es un modelo de lenguaje (LLM) al que se le dan *instrucciones*, un conjunto
  de *herramientas* que puede invocar y un *objetivo*. Decide, paso a paso, cómo alcanzarlo.
- Un **demo** conecta varios agentes con un backend pequeño y una interfaz para que una
  persona los vea trabajar. Cada demo vive en su propia carpeta bajo `src/` y es
  **totalmente independiente**: puedes clonar un solo demo y funcionará.
- Construimos agentes sobre **Microsoft Agent Framework (MAF)** para la orquestación y
  **Azure AI Foundry** para alojar modelos y agentes. No necesitas ser experto en ninguno
  para empezar: esta plantilla te da los patrones.
- Esta carpeta `templates/` te da dos cosas: un **scaffold de demo** (la forma estándar de
  un demo) y un **blueprint del framework agéntico** (la forma estándar y recomendada de
  construir los agentes que van dentro).

Si recuerdas una sola cosa: **copia una plantilla, rellena los `{{PLACEHOLDERS}}`, sigue el
checklist.** Ese es todo el flujo de trabajo.

### Requisitos previos

Instala esto una vez (las versiones son mínimos):

| Herramienta | Para qué | Dónde |
|---|---|---|
| **Python 3.12+** | Los agentes y el backend corren en Python | https://www.python.org/downloads/ |
| **Node 20+** (opcional) | Solo si tu demo tiene dashboard React | https://nodejs.org/ |
| **Azure CLI 2.60+** | Iniciar sesión y crear recursos en Azure | https://learn.microsoft.com/cli/azure/install-azure-cli |
| **Git** | Clonar el repositorio | https://git-scm.com/downloads |
| **VS Code** (recomendado) | Editor con extensiones Python + Bicep | https://code.visualstudio.com/ |

Necesitarás además una **suscripción de Azure** con permisos para crear recursos y cuota
para los modelos que use tu demo. ¿Sin Azure todavía? Ambos demos existentes funcionan con
datos simulados (mocks) cuando no hay endpoint configurado.

### Parte 1 — ejecuta tu primer demo

1. Clona el repo: `git clone <url>` y entra en `agentverse/src`.
2. Elige un demo: [`foundryairlines-demo`](../foundryairlines-demo/) (el más simple, 3
   agentes en secuencia) o [`insurance-ai-agents`](../insurance-ai-agents/) (completo, nivel
   empresa).
3. Sigue el README propio de ese demo (tiene su propio "Quick Start" paso a paso): crea el
   entorno virtual, copia `.env.example` a `.env`, arranca el backend y abre la interfaz.
4. Observa a los agentes trabajar. Ya tienes el modelo mental de un demo terminado.

### Parte 2 — crea tu propio demo

1. Copia el scaffold: `cp -r templates/demo-scaffold my-first-demo` (PowerShell:
   `Copy-Item -Recurse templates/demo-scaffold my-first-demo`).
2. Busca los marcadores: `grep -rn "{{" .` — cada coincidencia es algo que rellenar.
3. Rellénalos siguiendo el [checklist de copia](#copy-checklist), en este orden:
   `agentverse.yaml` → `README.md` → `.env.example` → `agents/` → `backend/`.
4. Mantén el demo **independiente**: no muevas código compartido a la raíz del repo. Cada
   demo lleva su propio `LICENSE`, `.github/`, `.env.example` y manifiesto.
5. Prepara el entorno: `python -m venv .venv`, actívalo e instala `requirements.txt`.

### Parte 3 — construye tu primer agente

Abre [`agentic-framework/README.md`](agentic-framework/README.md) al lado. Los 8 bloques de
construcción, en su forma más corta:

1. **Describe el agente** de forma declarativa: copia `agent-spec/` en
   `agents/<tu-agente>/` y edita `agent.yaml` (nombre, modelo, descripción).
2. **Escribe sus instrucciones** en `instructions.md`: quién es, qué debe hacer y la forma
   exacta de su salida (JSON estricto). Versiona este archivo.
3. **Dale herramientas** (opcional) en `tools.py` si necesita salir al mundo (BD, web, API).
4. **Elige un patrón de orquestación** en
   [`PATTERNS.md`](agentic-framework/PATTERNS.md). Empieza por el patrón **más simple que
   funcione**.
5. **Añade la red de seguridad**: guardrails para la entrada no confiable, observabilidad
   (trazas) y evals (casos dorados).
6. **Pasa el [checklist de producción](agentic-framework/CHECKLIST.md).**

### Parte 4 — añádelo al catálogo

1. Rellena `agentverse.yaml` en la raíz de tu demo (campos en
   [`catalog/README.md`](catalog/README.md)).
2. Valídalo: `python templates/catalog/build_catalog.py --validate my-first-demo/agentverse.yaml`.
3. Regenera el índice: `python templates/catalog/build_catalog.py --write`. Tu demo ya
   aparece en el catálogo.

### Glosario

Consulta la tabla en la sección [Glossary](#glossary) (los términos son iguales en ambos
idiomas).

### A dónde ir después

- Construir los agentes → [`agentic-framework/README.md`](agentic-framework/README.md)
- Elegir un patrón → [`agentic-framework/PATTERNS.md`](agentic-framework/PATTERNS.md)
- El manifiesto del catálogo → [`catalog/README.md`](catalog/README.md)
- Ejemplos completos → [`foundryairlines-demo`](../foundryairlines-demo/) ·
  [`insurance-ai-agents`](../insurance-ai-agents/)
