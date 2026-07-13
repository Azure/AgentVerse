# ---------------------------------------------------------------------------
# Resource group that holds the shared platform, the portal and every demo
# Container App. Demo-specific backing resources (Foundry, OpenAI, Cosmos,
# APIM, ...) are provisioned by each demo's own IaC hook, not here.
# ---------------------------------------------------------------------------
resource "azurerm_resource_group" "this" {
  name     = local.resource_group_name
  location = var.location
  tags     = local.common_tags
}

# ---------------------------------------------------------------------------
# Shared platform: Log Analytics + Container Registry + Container Apps
# Environment + a user-assigned identity with AcrPull. Every demo service and
# the portal run on this single environment so the portal can embed them.
# ---------------------------------------------------------------------------
module "platform" {
  source = "./modules/platform"

  name_prefix         = var.name_prefix
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.common_tags
}

# ---------------------------------------------------------------------------
# Shared AI backend (Strategy B): a single AIServices/Foundry account hosting
# every model used by every demo, plus Bing grounding and Content Safety. Lives
# in the same RG but may be in a different region (model availability).
# ---------------------------------------------------------------------------
data "azurerm_client_config" "current" {}

module "ai" {
  source = "./modules/ai"

  name_prefix           = var.name_prefix
  location              = var.ai_location
  resource_group_name   = azurerm_resource_group.this.name
  tags                  = local.common_tags
  identity_principal_id = module.platform.identity_principal_id
  deployer_object_id    = data.azurerm_client_config.current.object_id

  # Observability: report the Foundry project + AI resources into the shared
  # workspace / App Insights created by the platform module.
  log_analytics_workspace_id     = module.platform.log_analytics_workspace_id
  app_insights_id                = module.platform.app_insights_id
  app_insights_connection_string = module.platform.app_insights_connection_string
}

# ---------------------------------------------------------------------------
# Shared Cosmos DB (insurance claims store, keyless).
# ---------------------------------------------------------------------------
module "cosmos" {
  source = "./modules/cosmos"

  name_prefix           = var.name_prefix
  location              = var.ai_location
  resource_group_name   = azurerm_resource_group.this.name
  tags                  = local.common_tags
  identity_principal_id = module.platform.identity_principal_id

  log_analytics_workspace_id = module.platform.log_analytics_workspace_id
}

# ---------------------------------------------------------------------------
# One module instance per enabled demo. Builds each demo's image(s) into the
# shared ACR and deploys them as Container Apps in the shared environment.
# Container apps wait for the shared AI + Cosmos (incl. RBAC) to be ready so
# managed-identity calls succeed on first start.
# ---------------------------------------------------------------------------
module "demo" {
  source   = "./modules/demo"
  for_each = local.enabled_demos_merged

  depends_on = [module.ai, module.cosmos]

  demo_id             = each.key
  services            = each.value.services
  registration        = try(each.value.registration, {})
  registration_env    = try(local.registration_env[each.key], {})
  iac                 = try(each.value.iac, {})
  enable_registration = var.enable_agent_registration
  enable_iac          = var.enable_demo_iac

  name_prefix                  = var.name_prefix
  resource_group_name          = azurerm_resource_group.this.name
  repo_root                    = local.repo_root
  acr_login_server             = module.platform.acr_login_server
  acr_name                     = module.platform.acr_name
  container_app_environment_id = module.platform.container_app_environment_id
  identity_id                  = module.platform.identity_id
  tags                         = local.common_tags
}

# ---------------------------------------------------------------------------
# Portal Container App. Receives the map of demo_id => public web URL so the
# SPA can render one iframe tab per deployed demo.
# ---------------------------------------------------------------------------
module "portal" {
  source = "./modules/portal"

  name_prefix                  = var.name_prefix
  resource_group_name          = azurerm_resource_group.this.name
  repo_root                    = local.repo_root
  image_context                = var.portal_image_context
  acr_login_server             = module.platform.acr_login_server
  acr_name                     = module.platform.acr_name
  container_app_environment_id = module.platform.container_app_environment_id
  identity_id                  = module.platform.identity_id
  cpu                          = var.portal_cpu
  memory                       = var.portal_memory
  tags                         = local.common_tags

  # demo_id => https URL of each demo's web service (iframe target).
  demo_web_urls = { for k, m in module.demo : k => m.web_url }
}
