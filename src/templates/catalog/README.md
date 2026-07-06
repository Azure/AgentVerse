# AgentVerse Catalog

> How each independent demo advertises itself so AgentVerse can list them all in one place —
> **without** any shared, hand-maintained index.

---

## How it works

1. Every demo ships **one manifest** at its root: `agentverse.yaml`.
2. The manifest is validated against [`agentverse.schema.json`](agentverse.schema.json).
3. [`build_catalog.py`](build_catalog.py) scans all demos, validates each manifest, and
   generates a single catalog index (`catalog.json` / `CATALOG.md`).

Because the index is **generated**, demos stay fully independent: you never edit a shared
file to add a demo. Add the manifest, rerun the generator.

```
each demo/agentverse.yaml  ──►  build_catalog.py  ──►  catalog.json + CATALOG.md
```

---

## The manifest

Copy this into your demo root as `agentverse.yaml` and fill it in. Required fields:
`apiVersion`, `name`, `title`, `tagline`, `status`, `stack`, `agents`.

```yaml
apiVersion: agentverse/v1

name: {{demo-name}}                 # kebab-case, matches the folder name
title: {{Demo Title}}
tagline: {{One sentence describing what this demo shows}}
description: >-
  {{A longer paragraph: the scenario, the audience, and what it demonstrates.}}

status: experimental                # experimental | beta | stable | archived
difficulty: beginner                # beginner | intermediate | advanced
tags: [{{industry}}, {{capability}}]
owners: ["@{{your-handle}}"]

stack:
  framework: Microsoft Agent Framework
  backend: FastAPI
  frontend: {{React + Vite | Vanilla HTML/JS | none}}
  iac: {{Bicep | Terraform | none}}
  language: [Python]

orchestration: sequential           # see agentic-framework/PATTERNS.md

agents:
  - name: {{agent-one}}
    role: {{one line: what this agent does}}
    model: {{gpt-4.1}}
    tools: []
  - name: {{agent-two}}
    role: {{one line}}
    model: {{gpt-4.1}}
    tools: [{{web-grounding}}]

models: [{{gpt-4.1}}]
azureServices: [Azure AI Foundry]
capabilities: [tools, evals, observability]

entrypoints:
  quickstart: README.md#quick-start
  backend: uvicorn app.backend.main:app --port 8765
  frontend: app/frontend/index.html
  deploy: scripts/deploy.ps1

media: [images/screenshot.png]
links:
  docs: https://learn.microsoft.com/azure/ai-foundry/
```

See [`agentverse.schema.json`](agentverse.schema.json) for the full field reference,
allowed enum values, and validation rules.

---

## Using the generator

```bash
# from src/

# Validate one manifest
python templates/catalog/build_catalog.py --validate my-demo/agentverse.yaml

# Validate every demo's manifest (CI-friendly; non-zero exit on failure)
python templates/catalog/build_catalog.py --check

# Regenerate the catalog index files
python templates/catalog/build_catalog.py --write
```

The generator looks for `agentverse.yaml` files in every immediate subfolder of `src/`
(excluding `templates/`). Run `--check` in CI so a malformed manifest fails the build.

> **Dependencies:** `pyyaml` and `jsonschema`. Install with
> `pip install pyyaml jsonschema`.
