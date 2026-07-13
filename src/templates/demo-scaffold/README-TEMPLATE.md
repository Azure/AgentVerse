# AgentVerse standard demo README — template

> **📐 How to use this file.** Copy it into a demo as `README-PROPOSED.md` (for existing
> demos — each author decides independently whether to adopt it, adapt it, and make it
> the demo's README) or use it as the starting `README.md` for a brand-new demo. Replace
> every `<placeholder>` and delete the guidance blockquotes.
>
> **Self-containment rule:** the document must never reference the demo's existing
> README — it is written to *replace* it. Inline the essential content; link only to
> files that ship with the demo and survive adoption (infra/, docs, code paths).
>
> The document has two audiences and two parts, in this order:
>
> - **Part 1 · Business Brief** — for the person presenting the demo to a business
>   audience. Rule: **zero commands, zero unexplained acronyms.** Everything a
>   non-technical presenter needs to deliver the session solo lives here.
> - **Part 2 · Technical Brief** — for the person preparing and operating the demo
>   environment. Rule: **zero sales pitch.** The setup section must produce exactly the
>   state the Business Brief's verification checklist checks.
>
> Keep the parts self-contained: a Business Brief reader should never need to scroll
> into Part 2, and vice versa.

---

# `<Demo title>`

> `<One-line tagline: who it's for and what it shows, in plain words.>`

**Contents:** [Part 1 · Business Brief](#part-1--business-brief) — present the demo ·
[Part 2 · Technical Brief](#part-2--technical-brief) — prepare and operate it

---

## Part 1 · Business Brief

### 1.1 At a glance

| | |
|---|---|
| **Scenario** | `<industry + situation, in customer language>` |
| **Business outcome** | `<the one-line result the demo proves>` |
| **Best suited for** | `<which customer conversation / which audience in the room>` |
| **Duration** | `<X min>` |
| **Presenter effort** | `<solo-friendly / technical co-presenter recommended — and why>` |
| **Demo reliability** | `<live cloud calls vs. replay/sample data — how likely it is to behave identically every run>` |
| **Contingency** | `<the one sentence to fall back on if something fails live>` |

### 1.2 The story

> 3–5 short paragraphs, no code, no product names where a plain word works. The pain,
> the protagonist, what the agents do about it, and why this needs agents rather than
> a script.

`<story>`

### 1.3 The business case

> One row per KPI the audience is accountable for. Directional impact unless the demo
> itself measures the number; note where the KPI is visible on screen.

| Business KPI | Without agents | Impact demonstrated |
|---|---|---|
| `<KPI>` | `<baseline pain>` | `<impact + where visible>` |

`<Closing paragraph: which KPI carries the investment decision, and for whom.>`

### 1.4 Delivering the demo

#### Presenter verification (5 minutes before)

> Observable checks only — things the presenter can see, not commands to run. Each item
> corresponds to a state produced by the Technical Brief's setup section.

- [ ] `<e.g. "The demo page opens at the address provided and shows …">`

#### Demonstration sequence

> One step per beat, with minute marks and, where useful, the sentence that lands the
> point. Mark steps that suit technical rooms only. End on a business image, never on
> a terminal.

1. *(0–2 min)* `<what to show, what to state, the point it establishes>`
2. …

#### Key moments

- `<the 1–3 moments to emphasize, and the message each establishes>`

### 1.5 Anticipated questions

> The questions this demo reliably provokes, with honest drafted answers. Always cover:
> data privacy, accuracy/accountability, cost, and pilot timeline (as framing, not
> promises). Add demo-specific ones.

**"`<question>`"** — `<answer>`

### 1.6 From demo to next step

> The concrete follow-up to propose at the end of the session: a discovery workshop, a
> scoped pilot, what the customer would need to bring.

`<proposal>`

### 1.7 What this demo is not

> Expectation management: sample/mock data, demo status, what would change in a real
> deployment.

`<disclaimers>`

### Glossary

> Every acronym or term of art a presenter might be asked about. One line each.

- **`<term>`** — `<one-line explanation>`

> *To prepare the environment for this demo, share Part 2 with your technical contact.*

---

## Part 2 · Technical Brief

### 2.1 Technical profile

| | |
|---|---|
| **Status** | `<stable / beta / experimental — keep in sync with agentverse.yaml>` |
| **Orchestration** | `<sequential / orchestrator-workers / human-in-the-loop / …>` |
| **Models** | `<e.g. gpt-4.1, gpt-image-2>` |
| **Azure services** | `<e.g. Azure AI Foundry, APIM, Cosmos DB>` |
| **Stack** | `<framework · backend · frontend · IaC>` |
| **Runs locally without Azure?** | `<Yes (how) / No (why)>` |
| **Author** | `<@handle>` |

### 2.2 The architecture

> Embed the demo's existing diagram (ASCII block, Mermaid code, or `<img>` for
> SVG/PNG) rather than redrawing it or merely linking it — the reader must see the
> visual here. If the demo has several diagrams, embed the primary one and link the
> rest as files.

`<diagram — embedded>`

#### Components

| Component | Where | Role |
|---|---|---|
| `<component>` | `<path>` | `<one line>` |

#### The agents

| Agent | Kind | Model | Job |
|---|---|---|---|
| `<name>` | `<LLM agent / deterministic code / model call>` | `<model or —>` | `<one line>` |

### 2.3 Agentic patterns

> One row per pattern, free-form per demo. The last column equips whoever presents to
> explain the mechanism to a non-technical audience.

| Pattern | Where in this demo | Why it matters here | In business terms |
|---|---|---|---|
| `<pattern>` | `<file / component>` | `<one line>` | `<one-line analogy>` |

### 2.4 Technical setup

> Everything to run the day before a session, self-contained. The end state of this
> section is exactly what §1.4's presenter verification checks. Inline the essential
> steps and known failure modes; link only to files that ship with the demo.

- [ ] `<command / configuration step>`

### 2.5 Additional resources

> The catch-all: deployment paths, evals, CI/CD and governance, extra variants, API
> reference, cost & teardown notes, license. Pointers, not copies.

`<subsections as needed>`
