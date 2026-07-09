# AgentVerse — Global Deploy (`infra/`)

This folder contains the **global Terraform** that deploys every demo under
`src/` together, behind one **portal** (an Azure Container App) that shows one
tab per demo. It lives **outside `src/`** on purpose: the demos stay fully
independent, and this layer only orchestrates them.

> **TL;DR**
> ```powershell
> az login
> cd infra
> Copy-Item terraform.tfvars.example terraform.tfvars
> Copy-Item demos.auto.tfvars.example demos.auto.tfvars
> terraform init
> terraform apply
> terraform output portal_url
> ```

---

## What gets deployed

```
                        ┌──────────────────────────────────────────┐
                        │  Resource group  rg-<name_prefix>         │
                        │                                           │
  module.platform  ───► │  Log Analytics · ACR · Container Apps Env │
                        │  · user-assigned identity (AcrPull)       │
                        │                                           │
  module.portal    ───► │  Container App: portal (nginx SPA)        │
                        │     └─ iframe tab per demo (DEMOS_JSON)    │
                        │                                           │
  module.demo      ───► │  Container App(s) per demo (shared env)   │
   (for_each demos)     │     foundryairlines-demo: web             │
                        │     insurance-ai-agents:  backend + web   │
                        └──────────────────────────────────────────┘

  Each demo's OWN backing AI resources (Foundry, OpenAI, Cosmos, APIM, ...) are
  provisioned by that demo's OWN IaC, invoked as an optional gated hook.
```

**Ownership boundary (important):**

| Layer | Owns |
|---|---|
| `infra/` (this) | Shared platform, the portal, and each demo's **Container Apps** |
| each demo's IaC | That demo's **backing Azure AI resources** only (via the `iac` hook) |

This avoids two layers fighting over the same resources.

---

## The two contracts a demo satisfies

A demo plugs into the platform through **two** small contracts, linked by a
stable `demo_id`:

1. **Presentation** — `src/<demo>/agentverse.yaml` (aggregated into
   `src/catalog.json` by `src/templates/catalog/build_catalog.py`). Drives the
   tab title, tagline, agents and tags in the portal.
2. **Deployment topology** — an entry in `infra/demos.auto.tfvars` describing
   how to build and run the demo (its container services, ports, the one
   `is_web` service that becomes the iframe target, and optional agent /
   IaC hooks).

`demo_id` = the `demos` map key = the manifest `name`. See
[`../docs/adding-a-demo.md`](../docs/adding-a-demo.md) for the full walkthrough.

---

## Prerequisites

- **Azure CLI** ≥ 2.60, logged in (`az login`) with rights to create resources.
- **Terraform** ≥ 1.6.
- **Python 3.12+** (for the catalog + consistency scripts).
- No local Docker required — images are built server-side with `az acr build`.

---

## Step by step

### 1. Configure

```powershell
cd infra
Copy-Item terraform.tfvars.example terraform.tfvars       # global settings
Copy-Item demos.auto.tfvars.example demos.auto.tfvars     # demo topology
```

Edit `terraform.tfvars` (name prefix, region) and `demos.auto.tfvars` (which
demos are `enabled`). `insurance-ai-agents` ships **disabled** because its Bicep
provisions APIM (~30 min first run) and is costly — enable it deliberately.

> **Secrets:** never put keys in these files or in Terraform state. Only
> non-secret endpoints belong in a service's `env`. Prefer managed identity /
> Key Vault for secrets.

### 2. Regenerate the catalog and bake it into the portal

```powershell
python ../src/templates/catalog/build_catalog.py --write
Copy-Item ../src/catalog.json ../portal/public/catalog.json -Force
```

(`scripts/validate.ps1` does this for you.)

### 3. Deploy the shared platform + portal + demo containers

```powershell
terraform init
terraform apply
```

This creates the platform, builds each enabled demo's image(s) into ACR,
deploys the Container Apps, and wires the portal with each demo's URL.

### 4. Provision each demo's backing AI resources (optional hooks)

Two toggles turn the per-demo hooks on. They are **off by default** so the
platform can be applied on its own first.

```powershell
# Run each enabled demo's own IaC (foundryairlines Terraform / insurance Bicep):
terraform apply -var="enable_demo_iac=true"

# Register agents (idempotent). Requires each demo's Python env + az login:
terraform apply -var="enable_agent_registration=true"
```

Some steps **cannot** be automated and are marked `manual_prerequisite = true`
(e.g. FoundryAirlines' Bing grounding connection is a one-time portal step).
Get the exact commands to run by hand with:

```powershell
terraform output registration_commands
```

### 5. Open the portal

```powershell
terraform output portal_url
```

Each tab embeds a demo's frontend in an iframe, with an **Open in new tab**
button and a fallback if the demo blocks embedding (see notes below).

---

## Local validation (no Azure needed)

```powershell
./scripts/validate.ps1
```

Runs: manifest validation + catalog build, copies the catalog into the portal,
`terraform fmt -check` + `terraform validate`, and the catalog↔topology
consistency check. Use `-SkipTerraform` to skip the Terraform steps.

The same checks run in CI on every PR via
[`.github/workflows/platform-ci.yml`](../.github/workflows/platform-ci.yml),
which also builds every container image (portal + each demo) without pushing.

---

## iframe embedding notes

The portal embeds each demo's web URL. Embedding is **best-effort**:

- Demos that send `X-Frame-Options: DENY/SAMEORIGIN` or a restrictive CSP
  `frame-ancestors` will not render inside the frame — the portal shows a
  fallback with an **Open in new tab** button.
- Demos with an interactive **sign-in** flow (e.g. Entra ID / MSAL in
  `insurance-ai-agents`) generally should be opened in a new tab; embedded
  auth is unreliable.
- All demo URLs are HTTPS and WebSockets use `wss://` to avoid mixed content.

---

## State backend

State is **local** by default (fine for a single operator / prototyping). Once
this platform is shared, configure the `azurerm` backend in
[`versions.tf`](versions.tf) and run `terraform init -migrate-state`.

---

## Layout

```
infra/
├── versions.tf              # required_version + providers + (commented) backend
├── providers.tf             # azurerm / azapi / random
├── variables.tf             # global inputs + the `demos` topology contract
├── locals.tf                # naming, enabled-demo filter, repo root
├── main.tf                  # RG + platform + demo (for_each) + portal wiring
├── outputs.tf               # portal_url, demo_web_urls, registration_commands
├── terraform.tfvars.example
├── demos.auto.tfvars.example
├── modules/
│   ├── platform/            # Log Analytics + ACR + Container Apps Env + identity
│   ├── demo/                # generic: build image(s) + Container App(s) + hooks
│   └── portal/              # portal Container App (receives demo URL map)
└── scripts/
    ├── validate.ps1         # full local validation flow
    └── check-consistency.py # catalog <-> topology drift check
```
