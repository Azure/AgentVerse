# ---------------------------------------------------------------------------
# Global inputs
# ---------------------------------------------------------------------------

variable "subscription_id" {
  description = "Target Azure subscription id. Leave empty to use the Azure CLI default."
  type        = string
  default     = ""
}

variable "name_prefix" {
  description = "Short prefix used for all resource names (lowercase, no spaces)."
  type        = string
  default     = "agentverse"

  validation {
    condition     = can(regex("^[a-z][a-z0-9]{2,11}$", var.name_prefix))
    error_message = "name_prefix must be 3-12 chars, lowercase alphanumeric, starting with a letter."
  }
}

variable "location" {
  description = "Azure region for the shared platform and Container Apps."
  type        = string
  default     = "swedencentral"
}

variable "ai_location" {
  description = "Azure region for the shared AIServices account and model deployments. Must support all four models (gpt-4.1, gpt-image-2, gpt-5.4-mini, gpt-realtime-mini); swedencentral and eastus2 do."
  type        = string
  default     = "swedencentral"
}

variable "resource_group_name" {
  description = "Resource group that will hold the shared platform, portal and demo Container Apps. Created if it does not exist."
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags applied to every resource created by this configuration."
  type        = map(string)
  default = {
    project = "AgentVerse"
    managed = "terraform"
  }
}

# ---------------------------------------------------------------------------
# Portal
# ---------------------------------------------------------------------------

variable "portal_image_context" {
  description = "Build context (relative to repo root) for the portal container image."
  type        = string
  default     = "portal"
}

variable "portal_cpu" {
  description = "vCPU for the portal container app."
  type        = number
  default     = 0.5
}

variable "portal_memory" {
  description = "Memory for the portal container app."
  type        = string
  default     = "1Gi"
}

# ---------------------------------------------------------------------------
# Deploy behaviour toggles
# ---------------------------------------------------------------------------

variable "enable_agent_registration" {
  description = "When true, Terraform runs each enabled demo's agent-registration hook (local-exec) during apply. Requires `az login` and each demo's Python env. Manual prerequisites (e.g. Bing connection) are never automated."
  type        = bool
  default     = false
}

variable "enable_demo_iac" {
  description = "When true, Terraform runs each enabled demo's own IaC hook (foundryairlines Terraform / insurance Bicep) to provision its backing AI resources. Off by default so the shared platform can be applied independently."
  type        = bool
  default     = false
}

# ---------------------------------------------------------------------------
# Demo topology (deployment contract). Metadata for each demo lives in its
# agentverse.yaml (see catalog.json). This map describes HOW to build and run
# each demo; the `demo_id` key must match the demo's `name` in agentverse.yaml.
# ---------------------------------------------------------------------------

variable "contract_version" {
  description = "Version of the demo deployment contract this configuration implements."
  type        = string
  default     = "v1"
}

variable "demos" {
  description = "Map of demo_id => deployment topology. See docs/adding-a-demo.md."
  type = map(object({
    enabled = optional(bool, true)

    # One or more container services that make up the demo. Exactly one service
    # per enabled demo must set is_web = true (the iframe target for its tab).
    services = list(object({
      name         = string
      context      = string # build context, relative to repo root
      dockerfile   = string # Dockerfile path, relative to repo root
      target_port  = number
      is_web       = optional(bool, false)
      external     = optional(bool, true)
      cpu          = optional(number, 0.5)
      memory       = optional(string, "1Gi")
      min_replicas = optional(number, 0)
      max_replicas = optional(number, 1)
      env          = optional(map(string), {})
    }))

    # Agent-registration hook, executed only when enable_agent_registration = true.
    registration = optional(object({
      type                = optional(string, "none") # none | python_module | script | manual
      command             = optional(string, "")     # shell command run from repo root
      manual_prerequisite = optional(bool, false)    # true => needs a documented manual step
      notes               = optional(string, "")
    }), {})

    # Demo-specific IaC hook, executed only when enable_demo_iac = true.
    iac = optional(object({
      type    = optional(string, "none") # none | terraform | bicep | script
      command = optional(string, "")     # shell command run from repo root
      notes   = optional(string, "")
    }), {})
  }))
  default = {}

  validation {
    condition = alltrue([
      for k, d in var.demos :
      length([for s in d.services : s if try(s.is_web, false)]) == 1 if try(d.enabled, true)
    ])
    error_message = "Each enabled demo must declare exactly one service with is_web = true."
  }
}
