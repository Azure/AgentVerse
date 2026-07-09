# `infra/` — Azure resources (Terraform)

> AgentVerse demos default to **Terraform** for infrastructure-as-code (matching the
> foundryairlines demo). If your demo prefers Bicep, that's allowed — set `iac: Bicep` in
> `agentverse.yaml` and see the insurance demo for a reference.

## Files

```
infra/
├── main.tf            # Foundry account, model deployments, observability, hosting (Container Apps default / App Service)
├── variables.tf       # inputs (resource_group, location, names)
├── outputs.tf         # endpoints to copy into .env
└── terraform.tfvars.example   # copy to terraform.tfvars and fill in
```

## Usage

```bash
cd infra
terraform init
terraform plan  -var 'resource_group=rg-production-scheduling-demo' -var 'location=eastus2'
terraform apply -var 'resource_group=rg-production-scheduling-demo' -var 'location=eastus2'
```

After apply, copy the outputs into your `.env` (`PROJECT_ENDPOINT`, etc.):

```bash
terraform output
```

## What to provision

At minimum: an **Azure AI Foundry (AI Services) account**, a **project**, and the **model
deployments** your agents use. Add **APIM** (the AI gateway) and **Application Insights**
when you wire up guardrails/observability, and **Cosmos DB** if you use long-term memory.

## Rules

- **Managed identity, not keys.** Assign the app's identity the roles it needs; the app
  authenticates with `DefaultAzureCredential`.
- **Remote state for anything shared.** Local state is fine for a solo demo; use a remote
  backend (e.g. an Azure Storage container) once more than one person deploys.
- **Never commit `terraform.tfvars` or state** — they're in `.gitignore`.

## Notes from the first real apply (2026-07-09)

This configuration was applied for real for the first time on 2026-07-09
(subscription type: Microsoft managed environment). Full narrative in
[../CHANGELOG.md](../CHANGELOG.md); the operational lessons:

1. **Model versions age out.** `gpt-4.1/2025-04-14` was refused with
   `ServiceModelDeprecating` — models in deprecating state stay *listed* but reject
   *new* deployments. Before applying, check
   `az cognitiveservices model list -l <location> -o table` and pin versions that
   exist. Defaults now: chat `gpt-5.1/2025-11-13`, reasoning `gpt-5.4/2026-03-05`.
2. **The Foundry project is not yet Terraform-managed.** After apply, create it once
   with `az rest` (exact command in the comment at the bottom of `main.tf`). The
   account resource now sets `project_management_enabled = true`, which the project
   API requires.
3. **Local live runs need a data-plane role.** Subscription Owner is not enough for
   the Agents API. Grant your user **Azure AI Developer** on the Foundry account
   (some tenants also have the newer "Azure AI User" role — either works):
   ```bash
   MSYS_NO_PATHCONV=1 az role assignment create --role "Azure AI Developer" \
     --assignee-object-id "$(az ad signed-in-user show --query id -o tsv)" \
     --assignee-principal-type User \
     --scope "<foundry account resource id>"
   ```
4. **App Service quota can be zero.** Managed/sandbox subscriptions may carry an App
   Service limit of **0 Total VMs** (all tiers, F1 included), which fails
   `azurerm_service_plan` with a 401 quota error — region-scoped (eastus2 was 0,
   westus2 had capacity). This is why hosting defaults to **Container Apps**
   (`hosting = "containerapp"`): ACA draws on a different quota bucket and deployed
   fine in the same subscription and region. `hosting = "appservice"` +
   `webapp_location = "<region-with-quota>"` is the fallback.
5. **Windows on ARM:** the azurerm/archive providers ship no `windows_arm64` builds —
   `terraform init` fails on ARM64 Terraform. Install the `windows_amd64` Terraform
   zip side-by-side and use that binary (it runs fine under x64 emulation).
6. **Git Bash mangles scopes.** `/subscriptions/...` arguments get rewritten into
   Windows paths (surfacing as `MissingSubscription`). Prefix az commands with
   `MSYS_NO_PATHCONV=1`.
7. **Container Apps needs a one-time provider registration:**
   `az provider register --namespace Microsoft.App --wait` — otherwise the managed
   environment fails with `MissingSubscriptionRegistration`.
8. **`az acr build` has two Windows traps** (both handled by the `acr_build`
   provisioner in `main.tf`): it ignores `.dockerignore` when packing the upload —
   building from the demo root would ship `infra/` incl. `terraform.tfstate` and
   collide with the state lock mid-apply, so the context is staged from `app.zip` —
   and its log streaming crashes with `UnicodeEncodeError` on UTF-8 build output
   (the frontend's emoji) regardless of `PYTHONUTF8`/`PYTHONIOENCODING`, so the
   build is queued with `--no-logs` and polled via `az acr task show-run`.
