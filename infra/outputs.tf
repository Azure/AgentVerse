output "portal_url" {
  description = "Public URL of the unified AgentVerse portal."
  value       = module.portal.portal_url
}

output "demo_web_urls" {
  description = "Public web URL of each deployed demo (the iframe target for its tab)."
  value       = { for k, m in module.demo : k => m.web_url }
}

output "container_registry" {
  description = "Login server of the shared Azure Container Registry."
  value       = module.platform.acr_login_server
}

output "registration_commands" {
  description = "Manual agent-registration commands per demo. Run these after apply when enable_agent_registration = false, or to re-run registration."
  value       = { for k, m in module.demo : k => m.registration_command }
}

output "shared_ai" {
  description = "Shared AI backend endpoints and model deployment names used by every demo."
  value = {
    account_name            = module.ai.account_name
    project_endpoint        = module.ai.project_endpoint
    openai_endpoint         = module.ai.openai_endpoint
    ai_services_endpoint    = module.ai.ai_services_endpoint
    content_safety_endpoint = module.ai.content_safety_endpoint
    deployments             = module.ai.deployment_names
    bing_connection_name    = module.ai.bing_connection_name
  }
}

output "cosmos_endpoint" {
  description = "Endpoint of the shared Cosmos DB (insurance claims store)."
  value       = module.cosmos.endpoint
}
