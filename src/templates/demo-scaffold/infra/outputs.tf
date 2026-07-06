# Copy these into your .env after `terraform apply`.

output "foundry_endpoint" {
  description = "Base Foundry endpoint. Append /api/projects/<project> for PROJECT_ENDPOINT."
  value       = azurerm_ai_services.foundry.endpoint
}

output "model_deployment_name" {
  description = "MODEL_DEPLOYMENT_NAME for .env."
  value       = azurerm_cognitive_deployment.chat.name
}

output "foundry_principal_id" {
  description = "System-assigned identity — grant it the data-plane roles the app needs."
  value       = azurerm_ai_services.foundry.identity[0].principal_id
}
