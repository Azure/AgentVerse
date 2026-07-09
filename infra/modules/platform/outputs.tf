output "acr_name" {
  value = azurerm_container_registry.this.name
}

output "acr_login_server" {
  value = azurerm_container_registry.this.login_server
}

output "container_app_environment_id" {
  value = azurerm_container_app_environment.this.id
}

output "identity_id" {
  value = azurerm_user_assigned_identity.apps.id
}

output "identity_principal_id" {
  value = azurerm_user_assigned_identity.apps.principal_id
}

output "identity_client_id" {
  value = azurerm_user_assigned_identity.apps.client_id
}

output "log_analytics_workspace_id" {
  value = azurerm_log_analytics_workspace.this.id
}

output "app_insights_connection_string" {
  value = azurerm_application_insights.this.connection_string
}
