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

# ---- The app itself: one App Service, code shipped by Terraform -----------------
# Fully Terraform-driven deployment: `terraform apply` zips the demo (excluding
# infra/, envs, caches), deploys it to a Linux App Service, and wires config +
# managed identity. Code changes re-deploy on the next apply (the zip's hash
# changes). No pip, Node, or deploy scripts on the operator's machine.

data "archive_file" "app" {
  type        = "zip"
  source_dir  = "${path.module}/.."
  output_path = "${path.module}/app.zip"
  excludes = [
    "infra", ".venv", ".git", ".github", "__pycache__",
    ".env", "evals/last_report.json",
  ]
}

resource "azurerm_service_plan" "demo" {
  name                = "asp-${var.resource_group}"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  os_type             = "Linux"
  sku_name            = var.app_service_sku
}

resource "azurerm_linux_web_app" "demo" {
  name                = var.webapp_name
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  service_plan_id     = azurerm_service_plan.demo.id
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
  scope                = azurerm_cognitive_account.foundry.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_linux_web_app.demo.identity[0].principal_id
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
