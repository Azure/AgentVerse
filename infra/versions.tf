# Terraform and provider version constraints for the AgentVerse global deploy.
# Pinned to major versions to keep applies reproducible across contributors.
terraform {
  required_version = ">= 1.6"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    azapi = {
      source  = "azure/azapi"
      version = "~> 2.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  # Remote state is strongly recommended once this platform is shared.
  # Uncomment and configure, then run: terraform init -migrate-state
  #
  # backend "azurerm" {
  #   resource_group_name  = "rg-agentverse-tfstate"
  #   storage_account_name = "stagentversetfstate"
  #   container_name       = "tfstate"
  #   key                  = "global.tfstate"
  # }
}
