# Provider configuration. Authentication comes from `az login` (Azure CLI) or any
# other credential source supported by the azurerm/azapi providers.
provider "azurerm" {
  features {
    resource_group {
      # Allow Terraform to delete a resource group even if it still contains
      # resources that failed to provision cleanly (e.g. a Container Apps
      # Environment left in a Failed state after a regional capacity error).
      prevent_deletion_if_contains_resources = false
    }
  }

  # Optional: pin the target subscription explicitly instead of the CLI default.
  # subscription_id = var.subscription_id
}

provider "azapi" {}

provider "random" {}
