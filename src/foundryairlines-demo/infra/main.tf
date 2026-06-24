terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 4.0"
    }
    azapi = {
      source  = "azure/azapi"
      version = ">= 2.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

provider "azapi" {}

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------

variable "location" {
  description = "Azure region for all resources."
  type        = string
  default     = "eastus2"
}

# ---------------------------------------------------------------------------
# Random suffix (4-digit hex)
# ---------------------------------------------------------------------------

resource "random_id" "suffix" {
  byte_length = 2 # produces a 4-hex-char id
}

# ---------------------------------------------------------------------------
# Locals
# ---------------------------------------------------------------------------

locals {
  suffix = random_id.suffix.hex # e.g. "e67e"

  resource_group_name  = "rg-foundryair-${local.suffix}"
  foundry_account_name = "aifoundryair-${local.suffix}"
  project_name         = "prj-foundryair-${local.suffix}"
  bing_resource_name   = "bing-foundryair-${local.suffix}"

  tags = {
    SecurityControl = "Ignore"
  }
}

# ---------------------------------------------------------------------------
# 1. Resource Group
# ---------------------------------------------------------------------------

resource "azurerm_resource_group" "rg" {
  name     = local.resource_group_name
  location = var.location
  tags     = local.tags
}

# ---------------------------------------------------------------------------
# 2. Foundry (AI Services) account — kind = AIServices, SKU = S0
#    Created via azapi to set allowProjectManagement at creation time.
# ---------------------------------------------------------------------------

resource "azapi_resource" "foundry" {
  type      = "Microsoft.CognitiveServices/accounts@2025-04-01-preview"
  name      = local.foundry_account_name
  parent_id = azurerm_resource_group.rg.id
  location  = azurerm_resource_group.rg.location
  tags      = local.tags

  identity {
    type = "SystemAssigned"
  }

  body = {
    kind = "AIServices"
    sku = {
      name = "S0"
    }
    properties = {
      customSubDomainName    = local.foundry_account_name
      allowProjectManagement = true
    }
  }
}

# ---------------------------------------------------------------------------
# 3. Foundry project (data-plane resource — requires azapi)
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
    properties = {
      displayName = local.project_name
    }
    tags = local.tags
  }
}

# ---------------------------------------------------------------------------
# 4. Deploy gpt-4.1 (chat model used by both prompt agents)
# ---------------------------------------------------------------------------

resource "azurerm_cognitive_deployment" "gpt41" {
  name                 = "gpt-4.1"
  cognitive_account_id = azapi_resource.foundry.id

  model {
    format  = "OpenAI"
    name    = "gpt-4.1"
    version = "2025-04-14"
  }

  sku {
    name     = "GlobalStandard"
    capacity = 50
  }
}

# ---------------------------------------------------------------------------
# 5. Deploy gpt-image-2 (banner generation)
# ---------------------------------------------------------------------------

resource "azurerm_cognitive_deployment" "gpt_image_2" {
  name                 = "gpt-image-2"
  cognitive_account_id = azapi_resource.foundry.id

  model {
    format  = "OpenAI"
    name    = "gpt-image-2"
    version = "2026-04-21"
  }

  sku {
    name     = "GlobalStandard"
    capacity = 1
  }
}

# ---------------------------------------------------------------------------
# 6. Bing Grounding resource
# ---------------------------------------------------------------------------

resource "azapi_resource" "bing_grounding" {
  type                      = "Microsoft.Bing/accounts@2025-05-01-preview"
  name                      = local.bing_resource_name
  parent_id                 = azurerm_resource_group.rg.id
  location                  = "global"
  tags                      = local.tags
  schema_validation_enabled = false

  body = {
    kind = "Bing.Grounding"
    sku = {
      name = "G1"
    }
  }
}

# ---------------------------------------------------------------------------
# 7. Bing Grounding connection (project-scoped)
#    Wires the Bing resource into the Foundry project so the events-agent can
#    attach the Bing Grounding tool. Name must match BING_CONNECTION_NAME in
#    app/.env so bootstrap_agents.py can resolve it.
# ---------------------------------------------------------------------------

resource "azapi_resource_action" "bing_keys" {
  type        = "Microsoft.Bing/accounts@2025-05-01-preview"
  resource_id = azapi_resource.bing_grounding.id
  action      = "listKeys"
  method      = "POST"

  response_export_values = ["key1"]
}

resource "azapi_resource" "bing_connection" {
  type      = "Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview"
  name      = local.bing_resource_name
  parent_id = azapi_resource.project.id

  body = {
    properties = {
      category      = "GroundingWithBingSearch"
      target        = "https://api.bing.microsoft.com/"
      authType      = "ApiKey"
      isSharedToAll = true
      credentials = {
        key = azapi_resource_action.bing_keys.output.key1
      }
      metadata = {
        type       = "bing_grounding"
        ApiType    = "Azure"
        ResourceId = azapi_resource.bing_grounding.id
      }
    }
  }
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

output "project_endpoint" {
  description = "Foundry project endpoint for app/.env PROJECT_ENDPOINT."
  value       = "https://${local.foundry_account_name}.services.ai.azure.com/api/projects/${local.project_name}"
}

output "image_endpoint" {
  description = "OpenAI endpoint for app/.env IMAGE_ENDPOINT."
  value       = "https://${local.foundry_account_name}.openai.azure.com"
}
