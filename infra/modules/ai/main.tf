# ---------------------------------------------------------------------------
# Shared AI backend for AgentVerse (Strategy B: one AIServices/Foundry account
# hosts every model used by every demo). foundryairlines uses the project
# endpoint + gpt-4.1 + gpt-image-2 + Bing grounding; insurance-ai-agents uses
# the OpenAI endpoint + gpt-5.4-mini + gpt-realtime-mini + Content Safety.
# ---------------------------------------------------------------------------

resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
}

locals {
  account_name         = "${var.name_prefix}-foundry-${random_string.suffix.result}"
  project_name         = "${var.name_prefix}-proj-${random_string.suffix.result}"
  bing_resource_name   = "${var.name_prefix}-bing-${random_string.suffix.result}"
  content_safety_name  = "${var.name_prefix}-safety-${random_string.suffix.result}"
  services_ai_endpoint = "https://${local.account_name}.services.ai.azure.com"
  openai_endpoint      = "https://${local.account_name}.openai.azure.com"
  project_endpoint     = "${local.services_ai_endpoint}/api/projects/${local.project_name}"
}

# ---------------------------------------------------------------------------
# AIServices (Foundry) account. Created via azapi so allowProjectManagement can
# be set at creation time (required to host a Foundry project).
# ---------------------------------------------------------------------------
resource "azapi_resource" "account" {
  type      = "Microsoft.CognitiveServices/accounts@2025-04-01-preview"
  name      = local.account_name
  parent_id = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/resourceGroups/${var.resource_group_name}"
  location  = var.location
  tags      = var.tags

  identity {
    type = "SystemAssigned"
  }

  body = {
    kind = "AIServices"
    sku  = { name = "S0" }
    properties = {
      customSubDomainName    = local.account_name
      allowProjectManagement = true
      publicNetworkAccess    = "Enabled"
    }
  }

  response_export_values = ["properties.endpoint"]
}

data "azurerm_client_config" "current" {}

# ---------------------------------------------------------------------------
# Foundry project (data-plane resource) — gives foundryairlines its
# PROJECT_ENDPOINT and hosts the Bing grounding connection.
# ---------------------------------------------------------------------------
resource "azapi_resource" "project" {
  type      = "Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview"
  name      = local.project_name
  parent_id = azapi_resource.account.id
  location  = var.location

  identity {
    type = "SystemAssigned"
  }

  body = {
    properties = { displayName = local.project_name }
    tags       = var.tags
  }
}

# ---------------------------------------------------------------------------
# Model deployments. Chained via depends_on because concurrent deployments to
# the same Cognitive Services account frequently conflict.
# ---------------------------------------------------------------------------
resource "azurerm_cognitive_deployment" "gpt41" {
  name                 = "gpt-4.1"
  cognitive_account_id = azapi_resource.account.id

  model {
    format  = "OpenAI"
    name    = "gpt-4.1"
    version = "2025-04-14"
  }

  sku {
    name     = "GlobalStandard"
    capacity = var.gpt41_capacity
  }
}

resource "azurerm_cognitive_deployment" "gpt_image_2" {
  name                 = "gpt-image-2"
  cognitive_account_id = azapi_resource.account.id
  depends_on           = [azurerm_cognitive_deployment.gpt41]

  model {
    format  = "OpenAI"
    name    = "gpt-image-2"
    version = "2026-04-21"
  }

  sku {
    name     = "GlobalStandard"
    capacity = var.gpt_image_2_capacity
  }
}

resource "azurerm_cognitive_deployment" "gpt_5_4_mini" {
  name                 = "gpt-5.4-mini"
  cognitive_account_id = azapi_resource.account.id
  depends_on           = [azurerm_cognitive_deployment.gpt_image_2]

  model {
    format  = "OpenAI"
    name    = "gpt-5.4-mini"
    version = "2026-03-17"
  }

  sku {
    name     = "GlobalStandard"
    capacity = var.gpt_5_4_mini_capacity
  }
}

resource "azurerm_cognitive_deployment" "gpt_realtime_mini" {
  name                 = "gpt-realtime-mini"
  cognitive_account_id = azapi_resource.account.id
  depends_on           = [azurerm_cognitive_deployment.gpt_5_4_mini]

  model {
    format  = "OpenAI"
    name    = "gpt-realtime-mini"
    version = "2025-12-15"
  }

  sku {
    name     = "GlobalStandard"
    capacity = var.gpt_realtime_mini_capacity
  }
}

# ---------------------------------------------------------------------------
# Bing grounding resource + project connection (foundryairlines events-agent).
# ---------------------------------------------------------------------------
resource "azapi_resource" "bing" {
  type                      = "Microsoft.Bing/accounts@2025-05-01-preview"
  name                      = local.bing_resource_name
  parent_id                 = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/resourceGroups/${var.resource_group_name}"
  location                  = "global"
  tags                      = var.tags
  schema_validation_enabled = false

  body = {
    kind = "Bing.Grounding"
    sku  = { name = "G1" }
  }
}

resource "azapi_resource_action" "bing_keys" {
  type        = "Microsoft.Bing/accounts@2025-05-01-preview"
  resource_id = azapi_resource.bing.id
  action      = "listKeys"
  method      = "POST"

  response_export_values = ["key1"]
}

resource "azapi_resource" "bing_connection" {
  type      = "Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview"
  name      = var.bing_connection_name
  parent_id = azapi_resource.project.id

  body = {
    properties = {
      category      = "GroundingWithBingSearch"
      target        = "https://api.bing.microsoft.com/"
      authType      = "ApiKey"
      isSharedToAll = true
      credentials   = { key = azapi_resource_action.bing_keys.output.key1 }
      metadata = {
        type       = "bing_grounding"
        ApiType    = "Azure"
        ResourceId = azapi_resource.bing.id
      }
    }
  }
}

# ---------------------------------------------------------------------------
# Shared Content Safety account (insurance governance path).
# ---------------------------------------------------------------------------
resource "azurerm_cognitive_account" "content_safety" {
  name                  = local.content_safety_name
  location              = var.location
  resource_group_name   = var.resource_group_name
  kind                  = "ContentSafety"
  sku_name              = "S0"
  custom_subdomain_name = local.content_safety_name
  tags                  = var.tags
}

# ---------------------------------------------------------------------------
# RBAC. Container-app identity gets inference + agent-runtime roles; the
# Terraform executor gets Azure AI Developer so agent bootstrap can create
# agents and read the Bing connection.
# ---------------------------------------------------------------------------
locals {
  app_roles = toset([
    "Cognitive Services OpenAI User", # chat / image / realtime inference
    "Cognitive Services User",        # broader AI Services data plane
    "Azure AI Developer",             # run/manage Foundry project agents
  ])
}

resource "azurerm_role_assignment" "app" {
  for_each             = local.app_roles
  scope                = azapi_resource.account.id
  role_definition_name = each.value
  principal_id         = var.identity_principal_id
}

resource "azurerm_role_assignment" "app_content_safety" {
  scope                = azurerm_cognitive_account.content_safety.id
  role_definition_name = "Cognitive Services User"
  principal_id         = var.identity_principal_id
}

resource "azurerm_role_assignment" "deployer_ai_developer" {
  scope                = azapi_resource.account.id
  role_definition_name = "Azure AI Developer"
  principal_id         = var.deployer_object_id
}
