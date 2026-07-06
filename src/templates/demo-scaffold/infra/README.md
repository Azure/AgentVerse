# `infra/` — Azure resources (Terraform)

> AgentVerse demos default to **Terraform** for infrastructure-as-code (matching the
> foundryairlines demo). If your demo prefers Bicep, that's allowed — set `iac: Bicep` in
> `agentverse.yaml` and see the insurance demo for a reference.

## Files

```
infra/
├── main.tf            # resources: Foundry account + project, model deployments, (APIM, etc.)
├── variables.tf       # inputs (resource_group, location, names)
├── outputs.tf         # endpoints to copy into .env
└── terraform.tfvars.example   # copy to terraform.tfvars and fill in
```

## Usage

```bash
cd infra
terraform init
terraform plan  -var 'resource_group={{your-rg}}' -var 'location={{eastus2}}'
terraform apply -var 'resource_group={{your-rg}}' -var 'location={{eastus2}}'
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
