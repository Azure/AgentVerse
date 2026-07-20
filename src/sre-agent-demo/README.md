# Azure SRE Agent — AgentVerse demo

An interactive, **guided** walkthrough of the [Azure SRE Agent](https://learn.microsoft.com/azure/sre-agent/overview),
Microsoft's AI site-reliability agent for Azure workloads. It shows how the agent
turns an incident signal into a root cause and a **human-approved** remediation —
without you having to stand up a live agent.

> **Guided replay by default.** The demo ships with deterministic, seeded incident
> investigations and makes **no live Azure calls and takes no actions**. The portal
> tab always renders, at **zero cost and zero blast radius**. A read-only *live*
> path against a **dedicated sandbox** agent is scaffolded (see below) but off by
> default.

## What it shows

Three seeded incidents, each stepped through as an investigation timeline that
mirrors the real agent flow — **signal → observe (connectors) → hypothesis →
root cause → proposed remediation (approval)** — mapped to Well-Architected pillars:

| Scenario | Service | Root cause | WAF |
| --- | --- | --- | --- |
| Container App 5xx spike | Azure Container Apps | Revision halved the memory limit → OOM crash loop | Reliability, Ops |
| AKS CrashLoopBackOff | Azure Kubernetes Service | Secret rotation disabled the version the CSI mount pinned | Reliability, Security, Ops |
| API latency | Azure SQL Database | New query with no index → DTU saturation | Performance, Reliability |

The right panel explains the agent's real capabilities (connectors, modes,
approvals, RBAC, control/data-plane API, billing) with links to Microsoft Learn.

## Quick start

```bash
cd src/sre-agent-demo
pip install -r requirements.txt
uvicorn app.backend.main:app --port 8780
# open http://localhost:8780
```

No Azure credentials are needed in replay mode.

## API

| Method | Path | Description |
| --- | --- | --- |
| GET | `/healthz` | Liveness + current mode |
| GET | `/api/config` | Mode + rails (writes/approvals off) — drives the UI banner |
| GET | `/api/scenarios` | List seeded incidents |
| GET | `/api/scenarios/{id}` | Full investigation timeline |
| GET | `/api/context` | Capabilities + WAF notes + doc links |

## Deploy (unified stack)

Add an entry to `infra/demos.auto.tfvars` (one `is_web` service, port `8780`, no
`iac`, no `registration`) — see [`docs/adding-a-demo.md`](../../docs/adding-a-demo.md)
and `infra/demos.auto.tfvars.example`. Replay mode needs no injected env.

## Going live later (read-only, sandbox only)

The backend (`app/backend/config.py`) already carries the switches for a future
read-only proxy to a **real** SRE Agent. It stays in replay mode until
`SRE_AGENT_RESOURCE_ID` is set. Any live path **must** honour these rules
(from the design review):

- **Dedicated sandbox agent only** — never point the demo at production. The real
  blast radius is the *agent's own* execution identity/connectors, so scope those to
  disposable resources and prefer `ReadOnly`/`Review` mode.
- **The iframe URL is reachable without the portal's auth** — an env flag is not
  authorization. Keep **approvals disabled** (`SRE_AGENT_ALLOW_APPROVALS=false`) and
  **writes disabled** (`SRE_AGENT_ALLOW_WRITE=false`) in any shared/public deploy;
  never expose broad thread listing (use a per-session or allow-listed thread).
- **Fail closed** — re-check `actionConfiguration.mode` before every mutation;
  missing/unknown mode disables writes; rely on `SRE Agent Reader` RBAC for the
  read-only guarantee, not just a flag.
- **SSRF guard** — only contact the ARM-returned `agentEndpoint` when its host ends
  with `.azuresre.ai` over HTTPS. Never accept raw agent/thread ids from the browser.
- **Auth** — the managed identity mints an ARM token and a data-plane token for
  audience `https://azuresre.dev/.default`; pre-assign it `SRE Agent Reader`/`User`
  on the agent scope (it cannot self-assign RBAC).
- **Cost** — chat is billable and always-on flow accrues cost until the agent is
  **deleted** (`stop` is not enough); set monthly AAU caps and a cleanup runbook.
- **Don't hide breakage** — simulate only when deliberately unconfigured; if a live
  resource is configured but fails, surface "live integration unavailable" with a
  sanitized reason.

References: [API reference](https://learn.microsoft.com/azure/sre-agent/api-reference)
· [Agent modes](https://learn.microsoft.com/azure/sre-agent/agent-modes)
· [Pricing & billing](https://learn.microsoft.com/azure/sre-agent/pricing-billing)
· [Well-Architected Framework](https://learn.microsoft.com/azure/well-architected/).
