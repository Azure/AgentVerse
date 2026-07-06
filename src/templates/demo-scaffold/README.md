<!--
  This is the README TEMPLATE for a new AgentVerse demo. Replace every {{PLACEHOLDER}}.
  Keep the section order — it matches the two existing demos so readers know where to look.
  Delete this comment when done. See ../README.md (the hub) for the full getting-started guide.
-->

# {{Demo Title}}
### {{One-line subtitle: what this demo shows}}

[![License: MIT](https://img.shields.io/badge/License-MIT-2563EB?style=flat-square)](LICENSE)
[![Azure](https://img.shields.io/badge/Azure-AI%20Foundry-0078D4?style=flat-square&logo=microsoftazure&logoColor=white)](https://azure.microsoft.com/products/ai-foundry/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)

> {{Two or three sentences: the scenario, who it's for, and what it demonstrates.}}

🇬🇧 English · 🇪🇸 [Español](#-en-español)

---

## What it demonstrates

| Pillar | How it shows up here |
|---|---|
| 🤖 Multi-agent | {{N agents orchestrated with Microsoft Agent Framework}} |
| 🛡️ Guardrails | {{input/output validation, prompt-injection defense, content safety}} |
| 📊 Observability | {{tracing + token metrics}} |
| ✅ Evals | {{golden dataset gating changes}} |
| {{…}} | {{…}} |

## Architecture

```
{{ASCII or mermaid diagram of the agents and data flow.
  See ../agentic-framework/PATTERNS.md for the pattern you chose.}}
```

- **Orchestration pattern:** {{sequential | routing | orchestrator-workers | …}}
  (see [PATTERNS.md](../../templates/agentic-framework/PATTERNS.md))
- **Agents:** {{agent-one → agent-two → agent-three}}

---

## Prerequisites

- Python 3.12+ {{and Node 20+ if you have a dashboard}}
- Azure CLI ≥ 2.60 (`az login`)
- An Azure subscription with quota for {{gpt-4.1 / your models}} in {{eastus2 / your region}}

> This demo falls back to mock data when no Azure endpoint is configured, so you can run it
> without Azure to explore the flow. {{Delete if not true for your demo.}}

---

## Quick Start

### 1. Install

```bash
python -m venv .venv
. .venv/bin/activate                 # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and fill in your endpoints (see the file's comments).
az login
```

### 3. {{Bootstrap agents / provision resources — if applicable}}

```bash
{{python -m app.backend.bootstrap_agents}}
```

### 4. Run

```bash
# Backend
{{uvicorn app.backend.main:app --port 8765}}

# Frontend
{{open app/frontend/index.html}}
```

---

## Project structure

```
{{demo-name}}/
├── agents/              # the agents (built from ../agentic-framework/)
│   ├── shared/          # azure_client, guardrails, telemetry, memory, models
│   └── <agent>/         # agent.yaml, instructions.md, schemas.py, agent.py
├── backend/             # FastAPI + streaming (SSE/WebSocket)
├── frontend/            # {{vanilla HTML/JS | React dashboard}}
├── infra/               # Terraform (Azure resources)
├── evals/               # golden dataset + eval harness
├── scripts/             # deploy / run helpers
├── .github/             # CODEOWNERS, PR template, eval workflow
├── agentverse.yaml      # catalog manifest
├── .env.example
├── requirements.txt
└── LICENSE
```

---

## Deploy to Azure

```bash
cd infra
terraform init
terraform apply -var 'resource_group={{your-rg}}' -var 'location={{eastus2}}'
```

See [infra/README.md](infra/README.md) for variables and the resources created.

---

## Troubleshooting

- **{{`PROJECT_ENDPOINT` not set}}** — {{copy `.env.example` to `.env` and fill it in}}.
- **{{`DefaultAzureCredential` errors}}** — {{`az login` again, then re-run}}.
- {{Add the failure modes specific to your demo.}}

---

## License

MIT — see [LICENSE](LICENSE).

---
---

## 🇪🇸 En español

> {{Dos o tres frases: el escenario, para quién es y qué demuestra.}}

### Qué demuestra

{{Tabla de pilares: multi-agente, guardrails, observabilidad, evals, …}}

### Arquitectura

{{Diagrama de los agentes y el flujo de datos. Patrón de orquestación elegido — ver
[PATTERNS.md](../../templates/agentic-framework/PATTERNS.md).}}

### Requisitos previos

- Python 3.12+ {{y Node 20+ si hay dashboard}}
- Azure CLI ≥ 2.60 (`az login`)
- Suscripción de Azure con cuota para {{tus modelos}} en {{tu región}}

### Inicio rápido

1. **Instala:** `python -m venv .venv`, actívalo, `pip install -r requirements.txt`.
2. **Configura:** `cp .env.example .env`, rellena los endpoints, `az login`.
3. **{{Bootstrap / aprovisiona}}** si aplica.
4. **Ejecuta:** {{arranca el backend y abre el frontend}}.

### Estructura del proyecto

Ver el árbol de arriba (`agents/`, `backend/`, `frontend/`, `infra/` (Terraform), `evals/`,
`scripts/`, `.github/`, `agentverse.yaml`).

### Desplegar en Azure

```bash
cd infra && terraform init && terraform apply -var 'resource_group={{tu-rg}}' -var 'location={{eastus2}}'
```

### Licencia

MIT — ver [LICENSE](LICENSE).
