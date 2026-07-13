# AgentVerse standard demo README — template

> **📐 How to use this file.** Copy it into a demo as `README-PROPOSED.md` (for existing
> demos, out of respect for the author's original `README.md`, which stays canonical) or
> use it as the starting `README.md` for a brand-new demo. Replace every `<placeholder>`
> and delete the guidance blockquotes. Keep the section order — the whole point is that
> every AgentVerse demo presents itself the same way.

---

# `<Demo title>`

> `<One-line tagline: who it's for and what it shows, in plain words.>`

| | |
|---|---|
| **Industry / scenario** | `<e.g. Manufacturing · predictive maintenance>` |
| **Audience** | `<who you present this to>` |
| **Status** | `<stable / beta / experimental — keep in sync with agentverse.yaml>` |
| **Difficulty** | `<beginner / intermediate / advanced>` |
| **Orchestration** | `<sequential / orchestrator-workers / human-in-the-loop / …>` |
| **Models** | `<e.g. gpt-4.1, gpt-image-2>` |
| **Azure services** | `<e.g. Azure AI Foundry, APIM, Cosmos DB>` |
| **Stack** | `<framework · backend · frontend · IaC>` |
| **Runs locally without Azure?** | `<Yes (how) / No (why)>` |
| **Author & original docs** | `<@handle> · [README.md](README.md)` |

> Keep this card honest and factual — it is what makes demos comparable at a glance,
> and it should agree with `agentverse.yaml` (the catalog is generated from that file).

---

## 1 · The story

> 3–5 short paragraphs, no code. Answer, in order:
> - **The pain** — what breaks today, for whom, and what it costs.
> - **The protagonist** — the person in the scenario (a planner, a claims handler…).
> - **The agentic answer** — what the agents do about it, in one breath.
> - **Why agents (and not a script/batch job)** — the property that only an agentic
>   design gives you here: judgment, adaptation, grounding, governance…

`<story>`

---

## 2 · The business case

> Ground the demo in the KPIs the target audience is accountable for. One row per KPI.
> Be honest about quantification: use directional impact ("hours → minutes") unless the
> demo itself measures the number. Where the demo makes a KPI visible on screen, say
> where — a KPI the audience can watch move is worth more than a claimed percentage.

| Business KPI | Without agents | Impact demonstrated |
|---|---|---|
| `<KPI>` | `<baseline pain>` | `<direction of impact, and where it is visible in the demo if applicable>` |

`<One closing paragraph: the economic argument in prose — which of these KPIs carries
the investment decision, and for which stakeholder.>`

---

## 3 · The architecture

> One diagram + two tables. Reuse the author's existing diagram (ASCII, Mermaid or SVG)
> rather than redrawing it — formats may differ across demos; the *content* below is
> what's standardized.

`<diagram — embed or link the original>`

### Components

| Component | Where | Role |
|---|---|---|
| `<backend / frontend / gateway / data store…>` | `<path>` | `<one line>` |

### The agents

| Agent | Kind | Model | Job |
|---|---|---|---|
| `<name>` | `<LLM agent / deterministic code / model call>` | `<model or —>` | `<one line>` |

---

## 4 · Agentic patterns

> One row per pattern, in the demo's own words. Name the pattern, point at the exact
> code/config where it lives, and say why this demo needs it. If a pattern is described
> in [`templates/agentic-framework/PATTERNS.md`](../templates/agentic-framework/PATTERNS.md),
> linking the section is welcome but not required.

| Pattern | Where in this demo | Why it matters here |
|---|---|---|
| `<pattern>` | `<file / component>` | `<one line>` |

---

## 5 · Demonstration guide

> The runbook for presenting this demo. Someone who did not build the demo should be
> able to deliver it from this section alone. Keep the register formal — this section
> may be read verbatim in front of a customer.

**Duration:** `<X min>` · **Requires Azure live:** `<yes/no — and the fallback if unavailable>`

### Preparation checklist

- [ ] `<everything that must already be running / bootstrapped / cached>`

### Demonstration sequence

1. `<step: what to show, what to state, and the point it establishes>`
2. …

### Key moments

- `<the 1–3 moments to emphasize, and the message each one establishes>`

---

## 6 · Additional resources

> The catch-all. Whatever this demo has that the sections above don't cover: quick start
> & deployment (link to the author's docs rather than duplicating them), evals, CI/CD and
> governance, extra channels or variants, API reference, cost & teardown notes, license.
> Use `###` subsections; keep pointers, not copies.

`<subsections as needed>`
