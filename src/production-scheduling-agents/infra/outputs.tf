# Copy these into your .env after `terraform apply`.

output "foundry_endpoint" {
  description = "Base Foundry endpoint. Append /api/projects/<project> for PROJECT_ENDPOINT."
  value       = azurerm_cognitive_account.foundry.endpoint
}

output "model_deployment_name" {
  description = "MODEL_DEPLOYMENT_NAME for .env."
  value       = azurerm_cognitive_deployment.chat.name
}

output "reasoning_model_deployment_name" {
  description = "REASONING_MODEL_DEPLOYMENT_NAME for .env."
  value       = azurerm_cognitive_deployment.reasoning.name
}

output "application_insights_connection_string" {
  description = "APPLICATIONINSIGHTS_CONNECTION_STRING for .env."
  value       = azurerm_application_insights.this.connection_string
  sensitive   = true
}

output "foundry_principal_id" {
  description = "System-assigned identity — grant it the data-plane roles the app needs."
  value       = azurerm_cognitive_account.foundry.identity[0].principal_id
}

output "demo_url" {
  description = "The hosted planner dashboard. Open it."
  value       = "https://${azurerm_linux_web_app.demo.default_hostname}"
}
