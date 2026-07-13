# Shared platform for AgentVerse: registry, logging, Container Apps environment
# and a user-assigned identity that every container app uses to pull from ACR.

resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
}

locals {
  # ACR names must be globally unique, alphanumeric, 5-50 chars.
  acr_name = "${replace(var.name_prefix, "-", "")}acr${random_string.suffix.result}"
}

resource "azurerm_log_analytics_workspace" "this" {
  name                = "${var.name_prefix}-logs"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.tags
}

resource "azurerm_user_assigned_identity" "apps" {
  name                = "${var.name_prefix}-apps-id"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_container_registry" "this" {
  name                = local.acr_name
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "Standard"
  admin_enabled       = false # pull happens via the user-assigned identity below
  tags                = var.tags
}

# Grant the shared identity permission to pull images from the registry.
resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.this.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.apps.principal_id
}

resource "azurerm_container_app_environment" "this" {
  name                       = "${var.name_prefix}-cae"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id
  tags                       = var.tags
}

# Shared Application Insights (workspace-based). The insurance backend reads its
# connection string via APPLICATIONINSIGHTS_CONNECTION_STRING.
resource "azurerm_application_insights" "this" {
  name                = "${var.name_prefix}-appi"
  location            = var.location
  resource_group_name = var.resource_group_name
  workspace_id        = azurerm_log_analytics_workspace.this.id
  application_type    = "web"
  sampling_percentage = 10
  tags                = var.tags
}

# ---------------------------------------------------------------------------
# Azure Monitor: stream platform resource metrics/logs to the shared workspace.
# The CAE already ships app console/system logs via its built-in destination
# above, so only its metrics are captured here to avoid duplicate ingestion.
# ---------------------------------------------------------------------------
module "diag_cae" {
  source                     = "../diagnostics"
  name                       = "cae-to-law"
  target_resource_id         = azurerm_container_app_environment.this.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id
  logs_enabled               = false
}

module "diag_acr" {
  source                     = "../diagnostics"
  name                       = "acr-to-law"
  target_resource_id         = azurerm_container_registry.this.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id
}
