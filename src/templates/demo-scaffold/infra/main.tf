# {{Demo Title}} — Azure infrastructure (Terraform).
# Provisions an Azure AI Foundry account + project and the model deployments the agents use.
# Replace the {{PLACEHOLDERS}} and add resources (APIM, App Insights, Cosmos) as needed.

terraform {
  required_version = ">= 1.6"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
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

# Azure AI Foundry (AI Services) account — kind = AIServices.
resource "azurerm_ai_services" "foundry" {
  name                  = var.foundry_account_name
  resource_group_name   = azurerm_resource_group.this.name
  location              = azurerm_resource_group.this.location
  sku_name              = "S0"
  custom_subdomain_name = var.foundry_account_name

  identity {
    type = "SystemAssigned"
  }
}

# Chat model deployment used by the agents.
resource "azurerm_cognitive_deployment" "chat" {
  name                 = var.model_deployment_name
  cognitive_account_id = azurerm_ai_services.foundry.id

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

# TODO: add the Foundry project, APIM (AI gateway), Application Insights, Cosmos DB, and
# role assignments (managed identity) as your demo requires.
