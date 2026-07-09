# ---------------------------------------------------------------------------
# Serverless Cosmos DB (SQL API) for the insurance demo's claims store. Keyless:
# local auth is disabled and the container-app identity is granted the built-in
# Cosmos Data Contributor data-plane role. The insurance backend falls back to
# no-op mode if COSMOS_* is unset, so this is optional but enables persistence.
# ---------------------------------------------------------------------------

resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
}

resource "azurerm_cosmosdb_account" "this" {
  name                         = "${var.name_prefix}-cosmos-${random_string.suffix.result}"
  location                     = var.location
  resource_group_name          = var.resource_group_name
  offer_type                   = "Standard"
  kind                         = "GlobalDocumentDB"
  local_authentication_enabled = false
  # A subscription policy enforces private-only network access; pin to match the
  # deployed reality so plans stay clean and Terraform doesn't fight the policy.
  public_network_access_enabled = false
  tags                          = var.tags

  capabilities {
    name = "EnableServerless"
  }

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = var.location
    failover_priority = 0
  }
}

resource "azurerm_cosmosdb_sql_database" "this" {
  name                = var.database_name
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
}

resource "azurerm_cosmosdb_sql_container" "claims" {
  name                = var.container_name
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
  database_name       = azurerm_cosmosdb_sql_database.this.name
  partition_key_paths = ["/customer_id"]
}

# Built-in "Cosmos DB Built-in Data Contributor" data-plane role.
resource "azurerm_cosmosdb_sql_role_assignment" "app" {
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
  role_definition_id  = "${azurerm_cosmosdb_account.this.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = var.identity_principal_id
  scope               = azurerm_cosmosdb_account.this.id
}
