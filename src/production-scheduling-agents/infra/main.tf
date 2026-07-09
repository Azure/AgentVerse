# Production Scheduling AI Agents — Azure infrastructure (Terraform).
# Provisions: resource group, Azure AI Foundry (AI Services) account, the two model
# deployments the agents use (chat + reasoning), and Application Insights for
# observability. Add APIM (AI gateway) and Cosmos DB when you wire those up.

terraform {
  required_version = ">= 1.6"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
  # For shared deployments, configure a remote backend (delete for solo/local state):
  # backend "azurerm" {}
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "this" {
  name     = var.resource_group
  location = var.location
}

# Azure AI Foundry (AI Services) account.
# Uses azurerm_cognitive_account (azurerm_ai_services is deprecated in azurerm 4.x).
resource "azurerm_cognitive_account" "foundry" {
  name                  = var.foundry_account_name
  resource_group_name   = azurerm_resource_group.this.name
  location              = azurerm_resource_group.this.location
  kind                  = "AIServices"
  sku_name              = "S0"
  custom_subdomain_name = var.foundry_account_name

  # Required before a Foundry *project* can be created under this account
  # (the project itself is still created outside Terraform — see the note at
  # the bottom of this file).
  project_management_enabled = true

  identity {
    type = "SystemAssigned"
  }
}

# Chat model — used by constraint-monitor, schedule-orchestrator, schedule-dispatcher.
resource "azurerm_cognitive_deployment" "chat" {
  name                 = var.model_deployment_name
  cognitive_account_id = azurerm_cognitive_account.foundry.id

  model {
    format  = "OpenAI"
    name    = var.model_name
    version = var.model_version
  }

  sku {
    name     = "GlobalStandard"
    capacity = var.model_capacity
  }
}

# Reasoning model — used by scenario-simulator for trade-off analysis.
# Deployments on one account must be created sequentially, hence depends_on.
resource "azurerm_cognitive_deployment" "reasoning" {
  name                 = var.reasoning_model_deployment_name
  cognitive_account_id = azurerm_cognitive_account.foundry.id
  depends_on           = [azurerm_cognitive_deployment.chat]

  model {
    format  = "OpenAI"
    name    = var.reasoning_model_name
    version = var.reasoning_model_version
  }

  sku {
    name     = "GlobalStandard"
    capacity = var.reasoning_model_capacity
  }
}

# Observability — every scheduling decision is traced here.
resource "azurerm_log_analytics_workspace" "this" {
  name                = "log-${var.resource_group}"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_application_insights" "this" {
  name                = "appi-${var.resource_group}"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  workspace_id        = azurerm_log_analytics_workspace.this.id
  application_type    = "web"
}

# ---- The app itself ---------------------------------------------------------------
# Two hosting paths, selected by var.hosting (see variables.tf):
#   "containerapp" (default) — ACR + Azure Container Apps. Expandable (sidecars,
#     Dapr, more services later), scale-to-zero, and draws on a different quota
#     bucket than App Service (which was 0 VMs on the first-apply subscription).
#     The image is built IN AZURE by `az acr build` (no local Docker), triggered
#     by Terraform whenever the source hash changes.
#   "appservice" — zip deploy to a Linux App Service; Oryx installs deps server-side.
# Both wire the same app settings and a managed identity with model access.

locals {
  webapp_location = var.webapp_location != "" ? var.webapp_location : var.location
  # ACR names: alphanumeric only, globally unique.
  acr_name  = substr(replace("acr${var.webapp_name}", "-", ""), 0, 50)
  image_tag = substr(data.archive_file.app.output_sha, 0, 12)
}

# Zip of the app source. App Service deploys it directly; the Container Apps path
# uses its hash as the "did the code change?" trigger for image rebuilds.
data "archive_file" "app" {
  type        = "zip"
  source_dir  = "${path.module}/.."
  output_path = "${path.module}/app.zip"
  excludes = [
    "infra", ".venv", ".git", ".github", "__pycache__",
    ".env", "evals/last_report.json",
  ]
}

# ---- Hosting path A: App Service (var.hosting = "appservice") ---------------------

resource "azurerm_service_plan" "demo" {
  count               = var.hosting == "appservice" ? 1 : 0
  name                = "asp-${var.resource_group}"
  resource_group_name = azurerm_resource_group.this.name
  location            = local.webapp_location
  os_type             = "Linux"
  sku_name            = var.app_service_sku
}

resource "azurerm_linux_web_app" "demo" {
  count               = var.hosting == "appservice" ? 1 : 0
  name                = var.webapp_name
  resource_group_name = azurerm_resource_group.this.name
  location            = local.webapp_location
  service_plan_id     = azurerm_service_plan.demo[0].id
  https_only          = true

  zip_deploy_file = data.archive_file.app.output_path

  site_config {
    application_stack {
      python_version = "3.12"
    }
    app_command_line = "python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"
  }

  identity {
    type = "SystemAssigned"
  }

  app_settings = {
    SCM_DO_BUILD_DURING_DEPLOYMENT = "true" # Oryx runs pip install server-side
    WEBSITES_PORT                  = "8000"

    # Replay mode by default: deterministic demo, no model quota risk. For live
    # Foundry Agents, set PROJECT_ENDPOINT to the project endpoint (see README)
    # — the managed identity below already has model access.
    PROJECT_ENDPOINT                = var.webapp_project_endpoint
    MODEL_DEPLOYMENT_NAME           = azurerm_cognitive_deployment.chat.name
    REASONING_MODEL_DEPLOYMENT_NAME = azurerm_cognitive_deployment.reasoning.name

    APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.this.connection_string
  }
}

# The web app's managed identity may call the Foundry account's models.
resource "azurerm_role_assignment" "webapp_foundry" {
  count                = var.hosting == "appservice" ? 1 : 0
  scope                = azurerm_cognitive_account.foundry.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_linux_web_app.demo[0].identity[0].principal_id
}

# ---- Hosting path B: Container Apps (var.hosting = "containerapp", default) -------

resource "azurerm_container_registry" "demo" {
  count               = var.hosting == "containerapp" ? 1 : 0
  name                = local.acr_name
  resource_group_name = azurerm_resource_group.this.name
  location            = local.webapp_location
  sku                 = "Basic"
  admin_enabled       = false # identity-based pulls only
}

# One identity for the container app: pulls the image from ACR and (in live mode)
# calls the Foundry models. User-assigned because a system identity does not exist
# yet at image-pull time on first create.
resource "azurerm_user_assigned_identity" "demo" {
  count               = var.hosting == "containerapp" ? 1 : 0
  name                = "id-${var.webapp_name}"
  resource_group_name = azurerm_resource_group.this.name
  location            = local.webapp_location
}

resource "azurerm_role_assignment" "aca_acr_pull" {
  count                = var.hosting == "containerapp" ? 1 : 0
  scope                = azurerm_container_registry.demo[0].id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.demo[0].principal_id
}

resource "azurerm_role_assignment" "aca_foundry" {
  count                = var.hosting == "containerapp" ? 1 : 0
  scope                = azurerm_cognitive_account.foundry.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_user_assigned_identity.demo[0].principal_id
}

# Build the image in Azure (no local Docker): `az acr build` uploads a source
# context and builds server-side for linux/amd64. Re-runs whenever the source hash
# changes, so `terraform apply` keeps shipping code — same story as the zip deploy.
#
# IMPORTANT: the context is staged from app.zip, NOT the demo root. `az acr build`
# ignores .dockerignore when packing the upload, so building from the demo root
# would ship infra/ — including terraform.tfstate with its sensitive values — to
# the registry, and fails mid-apply anyway (state lock => Permission denied).
# app.zip already carries exactly the right excludes.
#
# The provisioner is PowerShell (this demo's first-run environment is Windows).
# On macOS/Linux swap the interpreter for bash and Expand-Archive for `unzip`.
resource "terraform_data" "acr_build" {
  count = var.hosting == "containerapp" ? 1 : 0

  triggers_replace = [local.image_tag]

  provisioner "local-exec" {
    working_dir = path.module
    interpreter = ["PowerShell", "-NoProfile", "-Command"]
    command     = <<-EOT
      $ErrorActionPreference = "Stop"
      $ctx = Join-Path $env:TEMP "prodsched-ctx-${local.image_tag}"
      if (Test-Path $ctx) { Remove-Item -Recurse -Force $ctx }
      Expand-Archive -Path "app.zip" -DestinationPath $ctx -Force
      # --no-logs, then poll: az's frozen Windows build crashes (UnicodeEncodeError)
      # streaming UTF-8 build logs (frontend emoji) through its cp1252 console layer,
      # and it ignores PYTHONUTF8/PYTHONIOENCODING. Queuing without logs is ASCII-safe.
      $runId = az acr build --registry ${azurerm_container_registry.demo[0].name} --image prodsched-demo:${local.image_tag} --no-logs --query runId -o tsv $ctx
      if ($LASTEXITCODE -ne 0 -or -not $runId) { exit 1 }
      Remove-Item -Recurse -Force $ctx
      Write-Output "Queued ACR run $runId; polling..."
      for ($i = 0; $i -lt 90; $i++) {
        Start-Sleep -Seconds 10
        $status = az acr task show-run --registry ${azurerm_container_registry.demo[0].name} --run-id $runId --query status -o tsv
        Write-Output "  run $runId : $status"
        if ($status -eq "Succeeded") { exit 0 }
        if ($status -in @("Failed", "Canceled", "Error", "Timeout")) {
          Write-Output "Build failed; fetch logs with: az acr task logs --registry ${azurerm_container_registry.demo[0].name} --run-id $runId"
          exit 1
        }
      }
      Write-Output "Timed out waiting for ACR run $runId"
      exit 1
    EOT
  }
}

resource "azurerm_container_app_environment" "demo" {
  count                      = var.hosting == "containerapp" ? 1 : 0
  name                       = "cae-${var.resource_group}"
  resource_group_name        = azurerm_resource_group.this.name
  location                   = local.webapp_location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id
}

resource "azurerm_container_app" "demo" {
  count                        = var.hosting == "containerapp" ? 1 : 0
  name                         = var.webapp_name
  resource_group_name          = azurerm_resource_group.this.name
  container_app_environment_id = azurerm_container_app_environment.demo[0].id
  revision_mode                = "Single"

  depends_on = [
    terraform_data.acr_build,
    azurerm_role_assignment.aca_acr_pull,
  ]

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.demo[0].id]
  }

  registry {
    server   = azurerm_container_registry.demo[0].login_server
    identity = azurerm_user_assigned_identity.demo[0].id
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 0 # scale to zero when idle; first request cold-starts
    max_replicas = 2

    container {
      name   = "demo"
      image  = "${azurerm_container_registry.demo[0].login_server}/prodsched-demo:${local.image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      # Replay mode by default — same policy as the App Service path.
      env {
        name  = "PROJECT_ENDPOINT"
        value = var.webapp_project_endpoint
      }
      env {
        name  = "MODEL_DEPLOYMENT_NAME"
        value = azurerm_cognitive_deployment.chat.name
      }
      env {
        name  = "REASONING_MODEL_DEPLOYMENT_NAME"
        value = azurerm_cognitive_deployment.reasoning.name
      }
      env {
        name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        value = azurerm_application_insights.this.connection_string
      }
      # DefaultAzureCredential must know which of the app's identities to use.
      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.demo[0].client_id
      }
    }
  }
}

# TODO: add the Foundry *project* (azapi: Microsoft.CognitiveServices/accounts/projects),
# APIM (AI gateway), and Cosmos DB as the implementation grows.
#
# Until the project is Terraform-managed, create it once after apply (this is what
# the first live deployment did on 2026-07-09 — see ../CHANGELOG.md):
#
#   az rest --method put \
#     --url "https://management.azure.com/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<foundry-account>/projects/<project-name>?api-version=2025-06-01" \
#     --body '{"location":"<location>","identity":{"type":"SystemAssigned"},"properties":{}}'
#
# The project endpoint (for PROJECT_ENDPOINT in .env) is then:
#   https://<foundry-account>.services.ai.azure.com/api/projects/<project-name>
