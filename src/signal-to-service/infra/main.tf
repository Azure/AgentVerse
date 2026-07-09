# Signal-to-Service — standalone Azure infrastructure (Terraform).
#
# Provisions everything the demo needs to run on its own:
#   * an Azure AI Foundry (AI Services) account + project
#   * a gpt-4.1 chat deployment (used by the 3 prompt agents)
#   * an Azure AI Search service + the SOP manuals index (RAG grounding)
#   * RBAC so the deploying principal can seed the index and the app can query it
#
# The unified AgentVerse deploy (repo-root /infra) does NOT call this file — it
# shares platform resources. This file is for running the demo standalone.

data "azurerm_client_config" "current" {}

resource "random_id" "suffix" {
  byte_length = 2 # 4 hex chars
}

locals {
  suffix               = random_id.suffix.hex
  resource_group_name  = "rg-${var.name_prefix}-${local.suffix}"
  foundry_account_name = "aif-${var.name_prefix}-${local.suffix}"
  project_name         = "prj-${var.name_prefix}-${local.suffix}"
  search_service_name  = "srch-${var.name_prefix}-${local.suffix}"
  search_index_name    = "signal-to-service-sops"

  project_endpoint = "https://${local.foundry_account_name}.services.ai.azure.com/api/projects/${local.project_name}"
  search_endpoint  = "https://${local.search_service_name}.search.windows.net"
}

# ---------------------------------------------------------------------------
# 1. Resource group
# ---------------------------------------------------------------------------

resource "azurerm_resource_group" "rg" {
  name     = local.resource_group_name
  location = var.location
  tags     = var.tags
}

# ---------------------------------------------------------------------------
# 2. Foundry (AI Services) account — created via azapi to set
#    allowProjectManagement at creation time.
# ---------------------------------------------------------------------------

resource "azapi_resource" "foundry" {
  type      = "Microsoft.CognitiveServices/accounts@2025-04-01-preview"
  name      = local.foundry_account_name
  parent_id = azurerm_resource_group.rg.id
  location  = azurerm_resource_group.rg.location
  tags      = var.tags

  identity {
    type = "SystemAssigned"
  }

  body = {
    kind = "AIServices"
    sku  = { name = "S0" }
    properties = {
      customSubDomainName    = local.foundry_account_name
      allowProjectManagement = true
    }
  }
}

# ---------------------------------------------------------------------------
# 3. Foundry project (data-plane resource — azapi)
# ---------------------------------------------------------------------------

resource "azapi_resource" "project" {
  type      = "Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview"
  name      = local.project_name
  parent_id = azapi_resource.foundry.id
  location  = azurerm_resource_group.rg.location

  identity {
    type = "SystemAssigned"
  }

  body = {
    properties = { displayName = local.project_name }
    tags       = var.tags
  }
}

# ---------------------------------------------------------------------------
# 4. gpt-4.1 chat deployment (diagnosis / knowledge / action agents)
# ---------------------------------------------------------------------------

resource "azurerm_cognitive_deployment" "chat" {
  name                 = var.model_name
  cognitive_account_id = azapi_resource.foundry.id

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

# ---------------------------------------------------------------------------
# 5. Azure AI Search — SOP manuals index (RAG). Keyless (RBAC-only).
# ---------------------------------------------------------------------------

resource "azurerm_search_service" "search" {
  name                         = local.search_service_name
  resource_group_name          = azurerm_resource_group.rg.name
  location                     = azurerm_resource_group.rg.location
  sku                          = var.search_sku
  local_authentication_enabled = false # force Entra ID (RBAC) — no admin keys
  tags                         = var.tags

  identity {
    type = "SystemAssigned"
  }
}

# ---------------------------------------------------------------------------
# 6. RBAC — let the deploying principal create the index + upload SOP chunks,
#    and query it at runtime (the app uses the same identity via az login when
#    run standalone; the unified deploy grants its UAMI Data Reader separately).
# ---------------------------------------------------------------------------

resource "azurerm_role_assignment" "search_service_contributor" {
  scope                = azurerm_search_service.search.id
  role_definition_name = "Search Service Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "search_data_contributor" {
  scope                = azurerm_search_service.search.id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Foundry OpenAI access for the deploying principal (to run the agents locally).
resource "azurerm_role_assignment" "openai_user" {
  scope                = azapi_resource.foundry.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = data.azurerm_client_config.current.object_id
}

# ---------------------------------------------------------------------------
# 7. Seed the SOP index (optional). Re-runs whenever a SOP file or the seeder
#    script changes. Requires Python + the app deps on the terraform machine.
# ---------------------------------------------------------------------------

resource "terraform_data" "seed_index" {
  count = var.seed_search_index ? 1 : 0

  triggers_replace = {
    sops   = sha1(join(",", [for f in fileset("${path.module}/../app/data/sops", "*.md") : filesha1("${path.module}/../app/data/sops/${f}")]))
    seeder = filesha1("${path.module}/../scripts/seed_search_index.py")
  }

  depends_on = [
    azurerm_search_service.search,
    azurerm_role_assignment.search_service_contributor,
    azurerm_role_assignment.search_data_contributor,
  ]

  provisioner "local-exec" {
    working_dir = "${path.module}/.."
    command     = "python scripts/seed_search_index.py"
    environment = {
      AZURE_SEARCH_ENDPOINT = local.search_endpoint
      AZURE_SEARCH_INDEX    = local.search_index_name
    }
  }
}
