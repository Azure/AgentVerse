> **📐 Proposed standardized README.** This file follows the AgentVerse standard demo
> presentation structure ([template](../templates/demo-scaffold/README-TEMPLATE.md)).
> The author's original [README.md](README.md) remains the canonical documentation —
> all setup detail lives there; this file organizes the demo for presentation.

---

# Insurance AI Agents

> Governed multi-agent claims processing: how an organization builds, governs and
> operates AI agents over a critical process with the same rigor demanded of
> enterprise software — packaged as a whitelabel, reskinnable demo.

| | |
|---|---|
| **Industry / scenario** | Insurance · auto claims processing (whitelabel — any regulated industry) |
| **Audience** | Enterprise architects, CISOs, regulated-industry IT (built to pass "a banking IT review") |
| **Status** | Stable |
| **Difficulty** | Advanced |
| **Orchestration** | Orchestrator–workers (MAF v1.4, with legacy-orchestrator fallback) |
| **Models** | gpt-5.4-mini · gpt-realtime-mini (voice) |
| **Azure services** | Azure AI Foundry · APIM (AI Gateway) · Cosmos DB · Container Apps · Static Web Apps · Entra ID |
| **Stack** | MAF · FastAPI + WebSocket · React 18 + TypeScript + Tailwind · Bicep |
| **Runs locally without Azure?** | Yes — the backend falls back to mocks when no Azure OpenAI endpoint is configured |
| **Author & original docs** | @aangell98 · [README.md](README.md) · [BRANDING.md](BRANDING.md) |

---

## 1 · The story

A customer crashes their car and reports the claim. What happens next inside the insurer
is a chain of careful, regulated work: extract the facts, score the risk, check for
fraud, apply the regulatory rules, decide, and leave an audit trail a regulator can
replay. It is exactly the kind of critical process enterprises *want* to hand to AI
agents — and exactly the kind their IT and compliance departments will not allow without
control.

That tension is the story of this demo. It does not merely show three agents (Intake,
Risk, Compliance) processing a claim end-to-end, over web and real-time voice. It shows
the **operating model around them**: every model call forced through an APIM AI Gateway
with content safety and token limits, users authenticated with Entra ID, every decision
persisted to Cosmos DB with a full audit trail, agent behavior guarded by a golden
dataset that runs on every pull request, and each agent's code owned by the team
accountable for it via CODEOWNERS.

The decisive scene: a regulator lowers a threshold, a developer edits one line in
`rules.py`, and the *software governance machinery* — not a human promise — ensures the
compliance team must approve the change and the eval gate must pass before it ships.
Agents governed like the critical software they are.

Why agents and not a rules engine? The judgment steps (understanding a free-text claim
report, weighing fraud signals) genuinely need a model. The demo's discipline is keeping
the model *inside* a governed lane: rules stay in reviewable code, policies in the
gateway, and evidence in the audit trail.

---

## 2 · The business case

The demo addresses the claims P&L and the compliance function simultaneously — the two
stakeholders whose approval any agentic deployment in insurance requires.

| Business KPI | Without agents | Impact demonstrated |
|---|---|---|
| **Claims cycle time (report → decision)** | Days of sequential manual handling across intake, risk and compliance desks | A complete, reasoned decision streamed in minutes; visible live in the auto-demo |
| **Straight-through processing rate** | Low: most claims touch multiple humans regardless of complexity | Routine claims decided end-to-end by agents; only flagged cases reach the operator review queue |
| **Cost per claim** | Proportional to manual touch time per desk | Human effort shifts from processing every claim to reviewing exceptions |
| **Fraud leakage** | Fraud signals reviewed inconsistently, under time pressure | Every claim receives a risk score and fraud probability, uniformly and auditable |
| **Regulatory change lead time** | Threshold changes travel through release cycles and manual test campaigns | A one-line change in `rules.py` ships through PR + CODEOWNERS + eval gate, applied without redeploy |
| **Audit readiness** | Evidence assembled retrospectively for each inspection | Every decision persisted with its full reasoning trail in Cosmos DB; gateway logs every model call |

The KPI that carries the investment decision in a regulated setting is not cycle time —
it is **regulatory change lead time and audit readiness**. Cost and speed benefits are
only realizable if compliance signs off, and the governance machinery is what makes that
signature possible.

---

## 3 · The architecture

The reference architecture lives in [images/architecture.svg](images/architecture.svg),
and [README.md](README.md#%EF%B8%8F-architecture) has the full Mermaid sequence of a
claim. In summary: Dashboard → Backend → Orchestrator → (Intake → Risk → Compliance),
with **every** model call routed through the APIM gateway, and results streamed back
over WebSocket while the audit trail lands in Cosmos DB.

### Components

| Component | Where | Role |
|---|---|---|
| React dashboard | [dashboard/](dashboard/) | Whitelabel UI: auto-demo slides, customer / operator / policy / security views |
| Backend | [backend/main.py](backend/main.py) | FastAPI + WebSocket streaming; Entra ID JWT auth ([backend/auth.py](backend/auth.py)) |
| Orchestrator | [agents/orchestrator/](agents/orchestrator/) | MAF v1.4 coordination ([maf_agent.py](agents/orchestrator/maf_agent.py)) with a legacy fallback |
| AI Gateway | [infra/apim-policy.xml](infra/apim-policy.xml) | APIM policies: managed identity, content safety, token limits, token metrics, trace |
| Persistence | [backend/claims_repository.py](backend/claims_repository.py) | Cosmos DB with the complete audit trail of every decision |
| Voice channel | [agents/voice/](agents/voice/) | gpt-realtime-mini IVR over the *same* pipeline |
| Evals | [evals/](evals/) | Golden dataset + harness, wired into CI |
| Infra | [infra/main.bicep](infra/main.bicep) | APIM + Azure OpenAI + Cosmos + managed identity (Bicep, subscription scope) |

### The agents

| Agent | Kind | Model | Job |
|---|---|---|---|
| `claims-intake` | LLM agent (+ content understanding) | gpt-5.4-mini | Structured extraction of the claim report into a typed schema |
| `risk-assessment` | LLM agent | gpt-5.4-mini | Risk scoring and fraud-probability estimation |
| `compliance` | LLM agent + code rules | gpt-5.4-mini | Applies regulatory rules ([rules.py](agents/compliance/rules.py)) to produce checks and a decision |
| `orchestrator` | LLM agent (MAF) | gpt-5.4-mini | Coordinates the three workers and the audit trail |

---

## 4 · Agentic patterns

| Pattern | Where in this demo | Why it matters here |
|---|---|---|
| **Orchestrator–workers** | [agents/orchestrator/maf_agent.py](agents/orchestrator/maf_agent.py) | Three specialized agents, one coordinator — each worker owns one competence and one team |
| **AI Gateway (centralized policy enforcement)** | [infra/apim-policy.xml](infra/apim-policy.xml) | No agent talks to the model directly; safety, quotas, metrics and audit are enforced in one place, keyless via managed identity |
| **Eval gate in CI** | [evals/run_evals.py](evals/run_evals.py) + `.github/workflows/eval-on-pr.yml` | Agent behavior is regression-tested like code: golden claims (including a prompt-injection case) gate every merge |
| **Governance-as-code** | `.github/CODEOWNERS` | A change to compliance logic *cannot* merge without the compliance team — org structure encoded in the repo |
| **Rules in code, judgment in the model** | [agents/compliance/rules.py](agents/compliance/rules.py) | Regulatory thresholds stay in reviewable, diffable Python; the LLM never owns the rulebook |
| **Multichannel, one pipeline** | [agents/voice/](agents/voice/) | Web and real-time voice reuse the same agents — channel is presentation, not logic |
| **Audited persistence** | [backend/claims_repository.py](backend/claims_repository.py) | Every decision replayable for a regulator (Cosmos DB audit trail) |
| **Graceful degradation to mocks** | backend startup | The full flow can be demonstrated with zero Azure dependencies |

---

## 5 · Demonstration guide

**Duration:** 12–15 min · **Requires Azure live:** no for the core flow (mocks); yes for
the gateway/security view and the live eval-gate pull request.

### Preparation checklist

- [ ] Backend running: `uvicorn main:app --port 8000` from `backend/` (venv + `pip install -r backend/requirements.txt`)
- [ ] Dashboard running: `npm install && npm run dev` in `dashboard/` → http://localhost:5173
- [ ] For the governance sequence: a browser tab on the GitHub repository, prepared to open a PR touching `agents/compliance/rules.py` — or a previously merged PR with the eval-gate comment, if time is constrained
- [ ] For the whitelabel point: familiarity with the `-BrandName` flag and [BRANDING.md](BRANDING.md)

### Demonstration sequence

1. Open the dashboard and start **"Play auto demo"** — the four stages (📝 Intake →
   📊 Risk → ✅ Compliance → 🏁 Decision) run with live token streaming. Explain each
   agent's contribution as it completes; note that earlier slides can be revisited while
   the remaining agents continue.
2. Switch to the **Operator view**: the human review queue. The point to establish:
   agents propose, accountable humans remain in the loop for flagged cases.
3. Switch to the **Security view**: APIM gateway events and Content Safety in action.
   The point to establish: every model call in the platform passed through the gateway.
4. Present the governance sequence: edit `HIGH_AMOUNT_THRESHOLD` in
   [agents/compliance/rules.py](agents/compliance/rules.py), open the pull request, and
   show CODEOWNERS requesting the compliance team's review and the Eval Gate commenting
   the impact table on the dataset cases.
5. Close with the whitelabel proposition: the same application under a different brand
   in minutes ([BRANDING.md](BRANDING.md); the `santander` branch is a complete example).

### Key moments

- The **rules.py pull request**: a regulatory circular arrives, one line changes, and the
  governance machinery — not a promise — guarantees compliance approval and a passing
  eval gate before it ships. This is the control a bank demands of critical software,
  applied to AI.
- The **eval-gate PR comment**, including the flagged `prompt_injection_attack` case:
  agent behavior regression-tested in CI like any other code.
- **Voice**: the same claims pipeline operating over a real-time conversation.

---

## 6 · Additional resources

### Whitelabel / reskinning

The default "Helix Insurance" brand is a placeholder. Palette, logo and name change via
`brand.ts` — see [BRANDING.md](BRANDING.md). One-command redeploy with a different brand:
`.\scripts\deploy.ps1 -BrandName "Your Brand"`.

### One-command Azure deployment

`.\scripts\deploy.ps1 -ResourceGroup rg-helix-demo -Location swedencentral` provisions
the Bicep infra, builds the backend into ACR → Container Apps, and publishes the
dashboard to Static Web Apps ([README.md §Quick Start](README.md#-quick-start)).

### Also in the repository

- [agents/hosted/](agents/hosted/) — the agent variant hosted in Azure AI Foundry.
- [agents/content_understanding/](agents/content_understanding/) — schema-based document
  extraction feeding intake.
- [evals/README.md](evals/README.md) — how the golden dataset and harness work.
- Identity: Entra ID (MSAL) for users, federated OIDC for CI/CD.
- Catalog manifest: [agentverse.yaml](agentverse.yaml). License: MIT.
