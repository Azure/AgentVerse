# Signal-to-Service — standalone infrastructure

Provisions everything the demo needs to run **on its own** (the unified AgentVerse
deploy in the repo-root `/infra` shares platform resources instead and does not
use this Terraform):

| Resource | Purpose |
|----------|---------|
| Azure AI Foundry account + project | Hosts the 3 prompt agents |
| `gpt-4.1` deployment | Model for diagnosis / knowledge / action agents |
| Azure AI Search (Basic, keyless/RBAC) | SOP manuals index for RAG grounding |
| Role assignments | Deploying principal can seed the index + run the agents |
| `terraform_data.seed_index` | Creates + fills the SOP index after apply |

## Prerequisites
* Terraform ≥ 1.5, `az login`
* Quota for `gpt-4.1` (GlobalStandard) in `var.location` (default `swedencentral`)
* Python + the app deps (`pip install -r ../requirements.txt`) on the machine
  running `terraform apply` — the seed hook shells out to
  `scripts/seed_search_index.py`. Set `-var seed_search_index=false` to skip and
  seed manually later.

## Deploy
```powershell
cd src/signal-to-service/infra
terraform init
terraform apply
```

Then wire the outputs into `../app/.env` and register the agents:
```powershell
terraform output           # project_endpoint, search_endpoint, search_index
cd ..
python -m app.backend.bootstrap_agents
```

## Notes
* **Keyless.** Search has `local_authentication_enabled = false`; the app and the
  seeder authenticate with Entra ID (`DefaultAzureCredential`). Grant the app's
  runtime identity `Search Index Data Reader` on the Search service.
* **Local-first.** Leave `AZURE_SEARCH_ENDPOINT` unset in `app/.env` to use the
  built-in local TF-IDF retriever with no Azure AI Search at all.
