output "account_id" {
  value = azapi_resource.account.id
}

output "account_name" {
  value = local.account_name
}

output "project_name" {
  value = local.project_name
}

# foundryairlines PROJECT_ENDPOINT.
output "project_endpoint" {
  value = local.project_endpoint
}

# insurance AZURE_OPENAI_ENDPOINT (also used for gpt-image-2 IMAGE_ENDPOINT).
output "openai_endpoint" {
  value = local.openai_endpoint
}

# insurance AZURE_AI_SERVICES_ENDPOINT (real resource endpoint).
output "ai_services_endpoint" {
  value = try(azapi_resource.account.output.properties.endpoint, local.services_ai_endpoint)
}

output "content_safety_endpoint" {
  value = azurerm_cognitive_account.content_safety.endpoint
}

output "bing_connection_name" {
  value = var.bing_connection_name
}

output "deployment_names" {
  value = {
    chat         = azurerm_cognitive_deployment.gpt41.name
    image        = azurerm_cognitive_deployment.gpt_image_2.name
    ins_chat     = azurerm_cognitive_deployment.gpt_5_4_mini.name
    voice        = azurerm_cognitive_deployment.gpt_realtime_mini.name
    ps_chat      = azurerm_cognitive_deployment.gpt_5_1.name
    ps_reasoning = azurerm_cognitive_deployment.gpt_5_4.name
  }
}

# Consumers should depend on this to guarantee model deployments + RBAC exist
# before their container apps start or agent bootstrap runs.
output "ready_id" {
  value = sha1(join(",", concat(
    [azurerm_cognitive_deployment.gpt41.id,
      azurerm_cognitive_deployment.gpt_image_2.id,
      azurerm_cognitive_deployment.gpt_5_4_mini.id,
      azurerm_cognitive_deployment.gpt_realtime_mini.id,
      azurerm_cognitive_deployment.gpt_5_1.id,
    azurerm_cognitive_deployment.gpt_5_4.id],
    [for r in azurerm_role_assignment.app : r.id],
    [azapi_resource.bing_connection.id],
  )))
}
