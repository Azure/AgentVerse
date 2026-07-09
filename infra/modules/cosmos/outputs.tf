output "endpoint" {
  value = azurerm_cosmosdb_account.this.endpoint
}

output "database_name" {
  value = azurerm_cosmosdb_sql_database.this.name
}

output "container_name" {
  value = azurerm_cosmosdb_sql_container.claims.name
}

output "ready_id" {
  value = azurerm_cosmosdb_sql_role_assignment.app.id
}
