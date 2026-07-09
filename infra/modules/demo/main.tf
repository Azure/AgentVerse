locals {
  services = { for s in var.services : s.name => s }

  # Internal base URL so a service can reach a sibling service inside the shared
  # Container Apps environment, e.g. "${AGENTVERSE_INTERNAL_PREFIX}backend".
  # Must match the Container App name scheme below (demo_id-service).
  internal_prefix = "http://${var.demo_id}-"

  # Deterministic image tag per service. Defaults to a short hash of the whole
  # build context (Dockerfile + every file that gets uploaded), so any change to
  # application code triggers a rebuild and rollout. Override per-service with
  # `image_tag` (or use CI) to pin a tag. A .dockerignore in each context keeps
  # node_modules/.venv out of the uploaded build context.
  image_tags = {
    for name, s in local.services : name => (
      s.image_tag != "" ? s.image_tag :
      substr(sha1(join("", concat(
        [filesha1("${var.repo_root}/${s.dockerfile}")],
        [for f in fileset("${var.repo_root}/${s.context}", "**") : filesha1("${var.repo_root}/${s.context}/${f}")]
      ))), 0, 12)
    )
  }

  images = {
    for name, s in local.services :
    name => "${var.acr_login_server}/${var.demo_id}-${name}:${local.image_tags[name]}"
  }

  web_service = one([for s in var.services : s.name if try(s.is_web, false)])
}

# ---------------------------------------------------------------------------
# Build each service image into the shared ACR. Runs `az acr build`, which
# uploads the context (honouring .dockerignore) and builds server-side, so no
# local Docker daemon is required. Re-runs only when the image tag changes.
# ---------------------------------------------------------------------------
resource "terraform_data" "image" {
  for_each = local.services

  triggers_replace = {
    image = local.images[each.key]
  }

  provisioner "local-exec" {
    working_dir = var.repo_root
    command     = "az acr build --registry ${var.acr_name} --image ${var.demo_id}-${each.key}:${local.image_tags[each.key]} --file ${each.value.dockerfile} --no-logs ${each.value.context}"
  }
}

# ---------------------------------------------------------------------------
# Deploy each service as a Container App on the shared environment.
# ---------------------------------------------------------------------------
resource "azurerm_container_app" "svc" {
  for_each = local.services

  # Container App names are limited to 32 chars. demo_id is already unique within
  # the platform, so it (plus the service name) is enough; the shared RG scopes it.
  name                         = "${var.demo_id}-${each.key}"
  resource_group_name          = var.resource_group_name
  container_app_environment_id = var.container_app_environment_id
  revision_mode                = "Single"
  tags                         = var.tags

  depends_on = [terraform_data.image]

  identity {
    type         = "UserAssigned"
    identity_ids = [var.identity_id]
  }

  registry {
    server   = var.acr_login_server
    identity = var.identity_id
  }

  ingress {
    external_enabled = each.value.external
    target_port      = each.value.target_port
    transport        = each.value.transport

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    min_replicas = each.value.min_replicas
    max_replicas = each.value.max_replicas

    container {
      name   = each.key
      image  = local.images[each.key]
      cpu    = each.value.cpu
      memory = each.value.memory

      # Always-available helper so a service can reach its siblings internally.
      env {
        name  = "AGENTVERSE_INTERNAL_PREFIX"
        value = local.internal_prefix
      }

      dynamic "env" {
        for_each = each.value.env
        content {
          name  = env.key
          value = env.value
        }
      }
    }
  }
}

# ---------------------------------------------------------------------------
# Optional demo-specific IaC hook (foundryairlines Terraform / insurance Bicep).
# Provisions the demo's backing AI resources only. Off unless enable_iac = true.
# ---------------------------------------------------------------------------
resource "terraform_data" "iac" {
  count = var.enable_iac && try(var.iac.type, "none") != "none" && try(var.iac.command, "") != "" ? 1 : 0

  triggers_replace = {
    command = var.iac.command
  }

  provisioner "local-exec" {
    working_dir = var.repo_root
    command     = var.iac.command
  }
}

# ---------------------------------------------------------------------------
# Optional agent-registration hook. Idempotent by contract. Off unless
# enable_registration = true. Manual prerequisites are never automated.
# ---------------------------------------------------------------------------
resource "terraform_data" "registration" {
  count = var.enable_registration && try(var.registration.type, "none") != "none" && try(var.registration.type, "none") != "manual" && try(var.registration.command, "") != "" ? 1 : 0

  triggers_replace = {
    command = var.registration.command
    env     = jsonencode(var.registration_env)
  }

  depends_on = [terraform_data.iac, azurerm_container_app.svc]

  provisioner "local-exec" {
    working_dir = var.repo_root
    command     = var.registration.command
    environment = var.registration_env
    # A missing Bing connection (a known manual portal step) must not fail the
    # whole apply — the demo still deploys, the agents can be bootstrapped later.
    on_failure = continue
  }
}
