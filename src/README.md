# AgentVerse — use cases

This folder contains every scenario that feeds the AgentVerse portfolio: four
independent, self-contained agentic AI demos, plus the shared templates and tooling
used to build and catalog them.

## How to navigate a demo

Every demo carries the same documents:

| Document | What it gives you |
|---|---|
| `README.md` | The author's current documentation — full setup and reference detail |
| `README-PROPOSED.md` | The proposed standardized README — fully self-contained, offered for each author to adopt (and adapt) as the demo's README. Two parts: **Part 1 · Business Brief** (story, business case, KPI impact, and a minute-by-minute guide to presenting it to a business audience — no commands, no jargon) and **Part 2 · Technical Brief** (architecture, agentic patterns, and the setup that prepares the environment) |
| `agentverse.yaml` | The catalog manifest — machine-readable facts (status, models, Azure services, entry points) that generate [CATALOG.md](CATALOG.md) |

New to the portfolio? Open a demo's `README-PROPOSED.md` and read Part 1 — it is
written to be understood with no technical background.

## The demos

| Demo | Industry | Use case | Highlights | Runs without Azure? |
|---|---|---|---|---|
| [foundryairlines-demo/](foundryairlines-demo/) | ✈️ Airline | Fill low-occupancy flights: three agents pick the emptiest flights, find a real upcoming event in each destination on the live web, and generate an event-aware promo banner per flight | The recommended **first demo** — beginner-friendly sequential orchestration, web grounding with source links, image generation | No — live cloud demo (cached replay available) |
| [insurance-ai-agents/](insurance-ai-agents/) | 🏦 Insurance | Governed claims processing: Intake, Risk and Compliance agents decide auto claims in minutes behind an AI gateway, with audit trail, human review queue, real-time voice channel and a whitelabel React dashboard | The **governance showcase** — built to pass an enterprise IT review: gateway policies, eval gate on every change, rules owned by accountable teams | Yes — core flow runs on built-in sample data |
| [production-scheduling-agents/](production-scheduling-agents/) | 🏭 Manufacturing | Self-healing production scheduling: a Sense → Simulate → Decide → Act loop absorbs disruptions (machine down, material delay, rush order), reschedules autonomously and escalates only ambiguous trade-offs to the planner | The **most presentation-safe demo** — replay mode has zero cloud dependency; business KPIs measured live on the dashboard; deterministic guardrails around the LLMs | **Yes — by default** (replay mode) |
| [signal-to-service/](signal-to-service/) | 🔧 Manufacturing | Predictive maintenance to field service: a telemetry anomaly is diagnosed, the correct maintenance procedure is retrieved **and cited**, a human approves, and a work order is created and scheduled to the right technician | The **human-in-the-loop** exemplar — event-triggered pipeline, grounded citations from the plant's own manuals, approval gate before any action | Partially — mocks are local, the three agents need a Foundry project |

### Choosing a demo for a conversation

- **First conversation about AI agents** → [foundryairlines-demo/](foundryairlines-demo/)
- **Compliance, governance or regulated-industry audience** → [insurance-ai-agents/](insurance-ai-agents/)
- **Operations / plant / supply-chain audience, or presenting solo without cloud access** → [production-scheduling-agents/](production-scheduling-agents/)
- **Maintenance / field-service audience, or "can the AI act safely on real systems?"** → [signal-to-service/](signal-to-service/)

## Shared resources

| Directory / file | Purpose |
|---|---|
| [templates/](templates/) | Everything needed to build a new demo consistently: [demo-scaffold/](templates/demo-scaffold/) (copyable standalone demo skeleton, including the standard [README-TEMPLATE.md](templates/demo-scaffold/README-TEMPLATE.md)), [agentic-framework/](templates/agentic-framework/) (the agent-creation blueprint with [PATTERNS.md](templates/agentic-framework/PATTERNS.md) and per-discipline guides), and [catalog/](templates/catalog/) (manifest schema + generator) |
| [tools/](tools/) | Tools for governing and operating agents in production (lifecycle, monitoring, maintenance) |
| [CATALOG.md](CATALOG.md) / [catalog.json](catalog.json) | The generated demo catalog — built from each demo's `agentverse.yaml` by `python templates/catalog/build_catalog.py`; never edit by hand |

## Adding a new demo

1. Copy [templates/demo-scaffold/](templates/demo-scaffold/) into a new folder here.
2. Write the README from [templates/demo-scaffold/README-TEMPLATE.md](templates/demo-scaffold/README-TEMPLATE.md) (Business Brief + Technical Brief).
3. Fill in `agentverse.yaml` and regenerate the catalog with `python templates/catalog/build_catalog.py`.
4. To join the unified AgentVerse portal deployment, see [docs/adding-a-demo.md](../docs/adding-a-demo.md).
