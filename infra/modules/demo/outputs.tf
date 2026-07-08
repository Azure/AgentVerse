output "web_url" {
  description = "Public HTTPS URL of the demo's web service (the iframe target)."
  value       = "https://${azurerm_container_app.svc[local.web_service].ingress[0].fqdn}"
}

output "service_urls" {
  description = "Public URL of every external service in the demo."
  value = {
    for name, app in azurerm_container_app.svc :
    name => try(app.ingress[0].external_enabled, false) ? "https://${app.ingress[0].fqdn}" : "internal"
  }
}

output "registration_command" {
  description = "The agent-registration command for manual execution (empty when none)."
  value       = try(var.registration.command, "")
}
