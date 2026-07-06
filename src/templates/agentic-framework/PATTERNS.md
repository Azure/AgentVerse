# Orchestration Patterns

> How to wire agents together. For each pattern: **what it is · when to use · when NOT to ·
> MAF construct · shape.** Runnable skeletons live in [`orchestration/`](orchestration/).

**Golden rule:** pick the simplest pattern that solves the problem. Move down this list only
when a measured limitation forces it. The patterns are ordered from simplest to most
open-ended.

| # | Pattern | Use it when | Existing example |
|---|---------|-------------|------------------|
| 1 | [Single-agent](#1-single-agent-augmented-llm) | One model + a few tools can do the job | — |
| 2 | [Sequential](#2-sequential-prompt-chaining) | Fixed steps, each feeds the next | foundryairlines |
| 3 | [Routing](#3-routing) | Input falls into distinct classes needing different handling | — |
| 4 | [Parallel](#4-parallel-fan-out--fan-in) | Independent subtasks that can run at once | foundryairlines (banners) |
| 5 | [Orchestrator–workers](#5-orchestratorworkers) | Subtasks unknown until runtime | insurance |
| 6 | [Evaluator–optimizer](#6-evaluatoroptimizer-reflection) | Output improves with critique loops | — |
| 7 | [Group chat / handoff](#7-group-chat--handoff) | Specialists collaborate/transfer control | — |
| 8 | [Human-in-the-loop](#8-human-in-the-loop) | A wrong action is costly or irreversible | insurance (operator) |

---

## 1. Single-agent (augmented LLM)

**What:** One agent with instructions, tools, and memory, looping until the goal is met.
The foundational unit — every pattern below is single agents composed.

**When:** The task is coherent and a handful of tools cover it (answer a question, extract
fields, call one API).

**When NOT:** The task has clearly separable stages with different instructions — use
sequential instead, so each stage stays small and testable.

**MAF:** A single `Executor` wrapping an `AzureAIAgentClient`, or a one-node workflow.

```
input ──► [ agent + tools ] ──► output
              ↑______↓ (tool loop)
```

---

## 2. Sequential (prompt chaining)

**What:** Fixed pipeline; each agent's output is the next agent's input.

**When:** Steps are known and ordered (analyze → enrich → generate). Highest
predictability, easiest to debug and cost.

**When NOT:** Steps are independent (use parallel) or unknown ahead of time (use
orchestrator-workers).

**MAF:** `WorkflowBuilder(...).add_edge(a, b).add_edge(b, c).build()`.

```
input ──► [A] ──► [B] ──► [C] ──► output
```

Reference: [`foundryairlines-demo`](../../foundryairlines-demo/) chains
flights → events → banners.

---

## 3. Routing

**What:** A classifier agent inspects the input and dispatches it to one of several
specialized downstream agents.

**When:** Inputs fall into distinct categories that each deserve different handling/prompts,
and mixing them into one prompt hurts quality.

**When NOT:** Categories are fuzzy or overlapping — one capable agent may do better than a
brittle router.

**MAF:** A router `Executor` that emits to different edges (conditional routing).

```
                 ┌─► [Handler A]
input ──► [Router]┼─► [Handler B] ──► output
                 └─► [Handler C]
```

---

## 4. Parallel (fan-out / fan-in)

**What:** Split work into independent subtasks, run them concurrently, then aggregate.

**When:** Subtasks don't depend on each other (score N items, generate N images). Cuts
latency; can also be used for voting/consensus.

**When NOT:** Later subtasks need earlier results — that's sequential.

**MAF:** Fan-out edges + an aggregator executor; or `asyncio.gather` inside one executor for
non-agent work.

```
              ┌─► [Worker] ─┐
input ──► fan ─┼─► [Worker] ─┼─► [Aggregate] ──► output
              └─► [Worker] ─┘
```

Reference: foundryairlines generates 5 banners concurrently with `asyncio.gather`.

---

## 5. Orchestrator–workers

**What:** A lead agent plans the work at runtime, delegates subtasks to worker agents, and
synthesizes their results.

**When:** You can't enumerate the subtasks in advance — they depend on the input (a claims
pipeline that adapts, a research task that branches).

**When NOT:** The steps are actually fixed — a hard-coded sequential/parallel graph is
cheaper and more predictable than paying a planner every run.

**MAF:** An orchestrator `Executor` that dynamically dispatches to worker executors and
collects outputs (the insurance demo's `orchestrator/` + `maf_agent.py`).

```
input ──► [Orchestrator] ──plans──► [Worker]…[Worker] ──► [Orchestrator synthesizes] ──► output
```

Reference: [`insurance-ai-agents`](../../insurance-ai-agents/) orchestrates
Intake → Risk → Compliance.

---

## 6. Evaluator–optimizer (reflection)

**What:** One agent produces, a second critiques against criteria, the producer revises —
loop until good enough or a max-iterations cap.

**When:** Quality measurably improves with feedback and you have clear evaluation criteria
(drafting, code generation, translation).

**When NOT:** No objective critique exists, or the extra passes blow the latency/cost
budget. Always cap the iterations.

**MAF:** A cycle between a generator and an evaluator executor with a stop condition.

```
input ──► [Generator] ──► [Evaluator] ──pass──► output
              ▲______________│ (revise, bounded)
```

---

## 7. Group chat / handoff

**What:** Several specialist agents share a conversation; control is handed off between them
until the task is done.

**When:** The problem needs different expertise interacting (a debate, a support agent
handing off to a billing agent), and the flow can't be pre-drawn.

**When NOT:** A fixed graph captures the flow — group chat's openness costs tokens and
predictability. Use it as a last resort.

**MAF:** Group-chat / handoff orchestration primitives; bound the turns.

```
input ──► [Agent A] ⇄ [Agent B] ⇄ [Agent C] ──► output   (handoff on demand)
```

---

## 8. Human-in-the-loop

**What:** Not an alternative to the others — a *cross-cutting* control. Insert a human
approval/edit step into any workflow above before a consequential action.

**When:** A wrong action is costly, irreversible, or regulated (payouts, deletions,
customer-facing commitments). Also for low-confidence outputs.

**How:** Pause the workflow, surface the decision to an operator UI, resume on approval.
Persist the decision to the audit trail.

```
… ──► [Agent] ──► [⏸ human review] ──approve──► [continue] ──► output
                              └──reject──► [halt / rework]
```

Reference: insurance demo routes low-confidence claims to `human_review` and an operator
queue.
