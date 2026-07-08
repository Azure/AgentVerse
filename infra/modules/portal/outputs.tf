output "portal_url" {
  value = "https://${azurerm_container_app.portal.ingress[0].fqdn}"
}
