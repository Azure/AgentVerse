output "resource_group" {
  description = "Resource group holding the demo resources."
  value       = azurerm_resource_group.rg.name
}

output "project_endpoint" {
  description = "Foundry project endpoint → app/.env PROJECT_ENDPOINT."
  value       = local.project_endpoint
}

output "model_deployment_name" {
  description = "Chat model deployment → app/.env MODEL_DEPLOYMENT_NAME."
  value       = azurerm_cognitive_deployment.chat.name
}

output "search_endpoint" {
  description = "Azure AI Search endpoint → app/.env AZURE_SEARCH_ENDPOINT."
  value       = local.search_endpoint
}

output "search_index" {
  description = "SOP index name → app/.env AZURE_SEARCH_INDEX."
  value       = local.search_index_name
}

output "bootstrap_agents_command" {
  description = "Run this after apply to register the 3 prompt agents in the project."
  value       = "PROJECT_ENDPOINT=${local.project_endpoint} python -m app.backend.bootstrap_agents"
}
