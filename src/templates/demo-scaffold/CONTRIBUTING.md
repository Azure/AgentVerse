# Contributing to {{Demo Title}}

> Conventions for this demo. It is a **self-contained** AgentVerse demo — it must run after
> being cloned on its own, so keep everything it needs inside this folder.
>
> 🇬🇧 English · 🇪🇸 [Español](#-en-español)

## Ground rules

- **Independence.** No dependency on repo-root files. This demo carries its own `LICENSE`,
  `.github/`, `.env.example`, and `agentverse.yaml`.
- **Build agents the AgentVerse way.** Follow
  [`../../templates/agentic-framework/`](../../templates/agentic-framework/): declarative
  `agent.yaml` + versioned `instructions.md` + typed `schemas.py`, model access via the
  gateway, guardrails, observability, evals.
- **Pass the [checklist](../../templates/agentic-framework/CHECKLIST.md)** before opening a PR.

## Layout & naming

- One agent per folder under `agents/<agent-name>/` (kebab-case).
- Shared plumbing in `agents/shared/` (one model client, imported everywhere).
- Prompts live in `instructions.md`, never inline in Python.
- Output is always a typed Pydantic schema.

## Workflow

1. Branch: `feat/<scope>` or `fix/<scope>`.
2. Make the change; update `instructions.md` / `schemas.py` together if the contract changes.
3. Add or update `evals/` golden cases; run them locally.
4. Fill the PR template; the eval gate must pass and the relevant CODEOWNER must approve.
5. Update `agentverse.yaml` if agents/models/capabilities changed, and re-run the catalog
   generator.

## Secrets

Never commit `.env` or keys. Use `DefaultAzureCredential` and the APIM gateway. `.env.example`
documents every variable the demo reads.

## 🇪🇸 En español

Convenciones de este demo, que es **autocontenido**: debe funcionar tras clonarse por sí
solo. Reglas: **independencia** (sin dependencias de la raíz del repo; lleva su propio
`LICENSE`, `.github/`, `.env.example`, `agentverse.yaml`); **construye agentes al estilo
AgentVerse** (ver [`../../templates/agentic-framework/`](../../templates/agentic-framework/):
`agent.yaml` declarativo + `instructions.md` versionado + `schemas.py` tipado, acceso al
modelo vía gateway, guardrails, observabilidad, evals); **pasa el
[checklist](../../templates/agentic-framework/CHECKLIST.md)** antes del PR. Layout: un agente
por carpeta en `agents/<nombre>/`, fontanería en `agents/shared/`, prompts en
`instructions.md` (nunca en código), salida siempre tipada (Pydantic). Flujo: rama
`feat/<scope>` → cambia (actualiza `instructions.md`/`schemas.py` juntos) → añade/actualiza
evals y córrelos → rellena la plantilla de PR (el eval gate debe pasar y aprobar el
CODEOWNER) → actualiza `agentverse.yaml` y regenera el catálogo. Nunca comprometas `.env` ni
claves.
