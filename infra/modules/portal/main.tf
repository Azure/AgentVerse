locals {
  dockerfile   = "${var.image_context}/Dockerfile"
  context_root = "${var.repo_root}/${var.image_context}"
  # Hash every file in the build context (not just the Dockerfile) so that any
  # change to the SPA assets, nginx config or entrypoint produces a new, unique
  # image tag and triggers a rebuild + rollout.
  context_files = fileset(local.context_root, "**")
  context_hash  = sha1(join("", [for f in local.context_files : filesha1("${local.context_root}/${f}")]))
  image_tag     = substr(local.context_hash, 0, 12)
  image         = "${var.acr_login_server}/portal:${local.image_tag}"
}

# Build the portal image into the shared ACR (server-side, no local Docker).
resource "terraform_data" "image" {
  triggers_replace = {
    image = local.image
    # Rebuild when the injected demo set changes so the baked config can refresh.
    demos = jsonencode(var.demo_web_urls)
  }

  provisioner "local-exec" {
    working_dir = var.repo_root
    command     = "az acr build --registry ${var.acr_name} --image portal:${local.image_tag} --file ${local.dockerfile} --no-logs ${var.image_context}"
  }
}

resource "azurerm_container_app" "portal" {
  name                         = "${var.name_prefix}-portal"
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
    external_enabled = true
    target_port      = 8080
    transport        = "auto"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "portal"
      image  = local.image
      cpu    = var.cpu
      memory = var.memory

      # The entrypoint turns this into a runtime config.js the SPA reads, so the
      # iframe URLs can change without rebuilding the image.
      env {
        name  = "DEMOS_JSON"
        value = jsonencode(var.demo_web_urls)
      }
    }
  }
}
