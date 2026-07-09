# Adding a demo to the AgentVerse platform

> **This is the platform memory.** Read it before building a new use case. It
> explains *what we are building*, *why*, and the exact **contract** every new
> demo must satisfy to be deployed by the global deploy and shown in the portal.
> Keep it up to date — it is the single source of truth for onboarding.

---

## The vision (what we want to do)

AgentVerse is a **growing catalog of independent agent demos** that we can show
**all together, in one place**:

- Every demo under `src/` is **self-contained** and runs on its own. We never
  move shared code to the repo root; a demo must still work if cloned alone.
- One **portal** (an Azure Container App) opens on a **landing page** that
  introduces AgentVerse and lists **every catalog demo as a card** (title,
  tagline, description, status). It also presents **one tab per demo** and embeds
  each demo's frontend in an iframe, so a presenter can walk through every demo
  from a single URL.
- One **global Terraform deploy** in [`infra/`](../infra/) provisions a shared
  platform, deploys all enabled demos, and (optionally) registers their agents
  — in one place.
- The platform is **catalog-driven**: adding a demo means adding metadata and a
  small deployment entry, never editing a hand-maintained list.

Because of this, a new demo integrates through **two small contracts** and
nothing else.

---

## The contract (two files, linked by `demo_id`)

`demo_id` is a stable, kebab-case id. It is **both**:

- the folder name under `src/` and the `name:` in the demo's `agentverse.yaml`
  (presentation), **and**
- the key in the `demos` map in `infra/demos.auto.tfvars` (deployment).

These must match exactly. That single id links “what to show” with “how to run”.

### Contract 1 — Presentation metadata (`src/<demo_id>/agentverse.yaml`)

Drives the demo's tab **and its landing-page card** in the portal (title,
tagline, description, agents, tags) and its row in `catalog.json` / `CATALOG.md`.
The landing card is generated automatically from this manifest — every demo you
add appears on the home page with no extra step. Write a clear one-line
`tagline` and a short-paragraph `description`: those are what the card shows.

- Copy the manifest from
  [`src/templates/catalog/README.md`](../src/templates/catalog/README.md) or
  from an existing demo.
- Validate it:
  ```bash
  python src/templates/catalog/build_catalog.py --validate src/<demo_id>/agentverse.yaml
  ```
- Required fields: `apiVersion`, `name`, `title`, `tagline`, `status`, `stack`,
  `agents`. Full reference:
  [`agentverse.schema.json`](../src/templates/catalog/agentverse.schema.json).

### Contract 2 — Deployment topology (`infra/demos.auto.tfvars`)

Describes how to build and run the demo. Add an entry keyed by `demo_id`:

```hcl
demos = {
  my-new-demo = {
    enabled = true

    services = [
      {
        name        = "web"                      # the user-facing frontend
        context     = "src/my-new-demo"          # build context (repo-root relative)
        dockerfile  = "src/my-new-demo/Dockerfile"
        target_port = 8080
        is_web      = true                        # EXACTLY ONE service per demo
        external    = true
        env         = {}                          # non-secret config only
      },
      # add more services (e.g. a separate backend) as needed
    ]

    # Optional: provision the demo's backing AI resources (its own IaC).
    iac = {
      type    = "terraform"                       # terraform | bicep | script | none
      command = "pwsh -NoProfile -Command \"Set-Location src/my-new-demo/infra; terraform init; terraform apply -auto-approve\""
    }

    # Optional: register persistent agents (must be idempotent).
    registration = {
      type    = "python_module"                   # python_module | script | manual | none
      command = "pwsh -NoProfile -Command \"Set-Location src/my-new-demo; python -m app.backend.bootstrap_agents\""
      manual_prerequisite = false                 # true if a manual step is unavoidable
    }
  }
}
```

Rules the platform enforces:

- **Exactly one** service per enabled demo has `is_web = true` — its public URL
  becomes the iframe target for the tab.
- Paths are **relative to the repo root**.
- **No secrets** in tfvars or Terraform state — only non-secret endpoints in a
  service `env`. Use managed identity / Key Vault for secrets.
- Services reach each other over the shared environment via the injected
  `AGENTVERSE_INTERNAL_PREFIX` env var (e.g. a frontend proxies to
  `${AGENTVERSE_INTERNAL_PREFIX}backend`).

---

## Packaging requirements

Each demo must be buildable into container image(s):

- **Provide a `Dockerfile`** for every service. The `is_web` service must serve
  a browser-loadable UI on its `target_port`.
  - *Single-container demo* (like `foundryairlines-demo`): the backend serves
    the UI and the API from one image.
  - *Separate frontend + backend* (like `insurance-ai-agents`): a `web` image
    (nginx serving the built SPA, proxying `/api` and `/ws` to the backend) plus
    a `backend` image.
- **Add a `.dockerignore`** so `node_modules`, `.venv`, `.git`, build outputs and
  `.env` files never enter the build context.
- If the UI needs a sign-in flow, expect it to open **in a new tab** from the
  portal rather than embed (see the iframe notes in the infra README).

---

## Checklist for a new demo

- [ ] Folder `src/<demo_id>/` is self-contained and runs on its own.
- [ ] `src/<demo_id>/agentverse.yaml` present and validates against the schema.
- [ ] `Dockerfile` + `.dockerignore` for each service; the `is_web` service
      serves a UI on its `target_port`.
- [ ] Entry added to `infra/demos.auto.tfvars` with exactly one `is_web` service.
- [ ] `demo_id` matches in both the manifest and the tfvars key.
- [ ] Any agent registration is **idempotent**; manual-only steps are marked
      `manual_prerequisite = true` and documented in the demo README.
- [ ] No secrets in tfvars/state; only non-secret endpoints in `env`.
- [ ] Local validation passes:
      ```powershell
      ./infra/scripts/validate.ps1
      ```
- [ ] Catalog regenerated and baked into the portal
      (validate.ps1 does this; or run `build_catalog.py --write` + copy).

---

## How it flows end to end

```
src/<demo_id>/agentverse.yaml ──► build_catalog.py ──► src/catalog.json
                                                          │ (baked into portal image)
                                                          ▼
infra/demos.auto.tfvars ─► module.demo (build image + Container App) ─► demo web URL
                                                          │
                                                          ▼
                              module.portal (DEMOS_JSON = {demo_id: url}) ─► one iframe tab per demo
```

Add the two files, run local validation, `terraform apply`. The demo shows up
as a new tab — no shared index to hand-edit.

---

## Where to go next

- Build the agents themselves →
  [`src/templates/agentic-framework/`](../src/templates/agentic-framework/)
- Start a new demo from the scaffold →
  [`src/templates/demo-scaffold/`](../src/templates/demo-scaffold/)
- The catalog manifest format →
  [`src/templates/catalog/README.md`](../src/templates/catalog/README.md)
- The global deploy → [`infra/README.md`](../infra/README.md)
