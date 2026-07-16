# Copy these into your .env after `terraform apply`.

output "foundry_account_name" {
  description = "Actual account name (prefix + random suffix) — needed for the az rest project-create command."
  value       = azurerm_cognitive_account.foundry.name
}

output "foundry_endpoint" {
  description = "Base Foundry endpoint. Append /api/projects/<project> for PROJECT_ENDPOINT."
  value       = azurerm_cognitive_account.foundry.endpoint
}

output "project_endpoint" {
  description = "PROJECT_ENDPOINT (also auto-synced into ../.env; answers once the Foundry project exists)."
  value       = local.project_endpoint
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
  description = "The hosted planner dashboard. Open it. (null when hosting = \"none\")"
  value = (
    var.hosting == "containerapp" ? "https://${azurerm_container_app.demo[0].ingress[0].fqdn}" :
    var.hosting == "appservice" ? "https://${azurerm_linux_web_app.demo[0].default_hostname}" :
    null
  )
}
