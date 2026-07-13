locals {
  # Repo root is the parent of this infra/ folder. Build contexts in the demos
  # map are expressed relative to the repo root for readability.
  repo_root = abspath("${path.module}/..")

  resource_group_name = var.resource_group_name != "" ? var.resource_group_name : "rg-${var.name_prefix}"

  # Only enabled demos are deployed.
  enabled_demos = { for k, d in var.demos : k => d if try(d.enabled, true) }

  common_tags = merge(var.tags, {
    contractVersion = var.contract_version
  })

  # -------------------------------------------------------------------------
  # Computed environment injected into each demo service from the shared module
  # outputs (endpoints, deployment names, identity client id). Keyed by
  # demo_id => service name => env map. These override any static value in the
  # demos map, so tfvars stays free of endpoints that only exist after apply.
  # -------------------------------------------------------------------------
  computed_env = {
    "foundryairlines-demo" = {
      "web" = {
        PROJECT_ENDPOINT                      = module.ai.project_endpoint
        MODEL_DEPLOYMENT_NAME                 = module.ai.deployment_names.chat
        IMAGE_ENDPOINT                        = module.ai.openai_endpoint
        IMAGE_DEPLOYMENT                      = module.ai.deployment_names.image
        IMAGE_API_VERSION                     = "2025-04-01-preview"
        BING_CONNECTION_NAME                  = module.ai.bing_connection_name
        APPLICATIONINSIGHTS_CONNECTION_STRING = module.platform.app_insights_connection_string
        OTEL_SERVICE_NAME                     = "foundryairlines-demo"
        AZURE_CLIENT_ID                       = module.platform.identity_client_id
      }
    }
    "insurance-ai-agents" = {
      "backend" = {
        AZURE_OPENAI_ENDPOINT                 = module.ai.openai_endpoint
        AZURE_OPENAI_DEPLOYMENT               = module.ai.deployment_names.ins_chat
        AZURE_OPENAI_VOICE_DEPLOYMENT         = module.ai.deployment_names.voice
        AZURE_AI_SERVICES_ENDPOINT            = module.ai.ai_services_endpoint
        AZURE_CONTENT_SAFETY_ENDPOINT         = module.ai.content_safety_endpoint
        COSMOS_ENDPOINT                       = module.cosmos.endpoint
        COSMOS_DATABASE                       = module.cosmos.database_name
        COSMOS_CONTAINER                      = module.cosmos.container_name
        APPLICATIONINSIGHTS_CONNECTION_STRING = module.platform.app_insights_connection_string
        OTEL_SERVICE_NAME                     = "insurance-ai-agents"
        USE_APIM_GATEWAY                      = "false"
        AUTH_ENABLED                          = "false"
        AZURE_CLIENT_ID                       = module.platform.identity_client_id
      }
    }
    # Signal-to-Service uses the shared Foundry project + gpt-4.1. The unified
    # deploy relies on the bundled local RAG (no AZURE_SEARCH_ENDPOINT), so no
    # extra Azure AI Search is provisioned; the standalone infra/ still can.
    "signal-to-service" = {
      "web" = {
        PROJECT_ENDPOINT                      = module.ai.project_endpoint
        MODEL_DEPLOYMENT_NAME                 = module.ai.deployment_names.chat
        APPLICATIONINSIGHTS_CONNECTION_STRING = module.platform.app_insights_connection_string
        OTEL_SERVICE_NAME                     = "signal-to-service"
        AZURE_CLIENT_ID                       = module.platform.identity_client_id
      }
    }
    # Production-scheduling runs live on the shared Foundry project: gpt-5.1 for
    # the orchestrator (MODEL_DEPLOYMENT_NAME) and gpt-5.4 for the reasoning
    # scenario-simulator (REASONING_MODEL_DEPLOYMENT_NAME). Its UAMI already has
    # the agent + inference roles on the shared account.
    "production-scheduling-agents" = {
      "web" = {
        PROJECT_ENDPOINT                      = module.ai.project_endpoint
        MODEL_DEPLOYMENT_NAME                 = module.ai.deployment_names.ps_chat
        REASONING_MODEL_DEPLOYMENT_NAME       = module.ai.deployment_names.ps_reasoning
        APPLICATIONINSIGHTS_CONNECTION_STRING = module.platform.app_insights_connection_string
        OTEL_SERVICE_NAME                     = "production-scheduling-agents"
        AZURE_CLIENT_ID                       = module.platform.identity_client_id
      }
    }
  }

  # Environment for each demo's agent-registration hook (runs locally as the
  # Terraform executor, so it uses az-login creds — no AZURE_CLIENT_ID here).
  registration_env = {
    "foundryairlines-demo" = {
      PROJECT_ENDPOINT      = module.ai.project_endpoint
      MODEL_DEPLOYMENT_NAME = module.ai.deployment_names.chat
      BING_CONNECTION_NAME  = module.ai.bing_connection_name
    }
    "signal-to-service" = {
      PROJECT_ENDPOINT      = module.ai.project_endpoint
      MODEL_DEPLOYMENT_NAME = module.ai.deployment_names.chat
    }
  }

  # Demos with computed env merged into each service.
  enabled_demos_merged = {
    for k, d in local.enabled_demos : k => merge(d, {
      services = [
        for s in d.services : merge(s, {
          env = merge(try(s.env, {}), try(local.computed_env[k][s.name], {}))
        })
      ]
    })
  }
}
