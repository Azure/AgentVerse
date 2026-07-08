variable "demo_id" {
  description = "Stable demo id. Must match the demo's `name` in its agentverse.yaml."
  type        = string
}

variable "services" {
  description = "Container services that make up the demo."
  type = list(object({
    name         = string
    context      = string
    dockerfile   = string
    target_port  = number
    is_web       = optional(bool, false)
    external     = optional(bool, true)
    cpu          = optional(number, 0.5)
    memory       = optional(string, "1Gi")
    min_replicas = optional(number, 0)
    max_replicas = optional(number, 1)
    transport    = optional(string, "auto")
    env          = optional(map(string), {})
    image_tag    = optional(string, "")
  }))
}

variable "registration" {
  description = "Agent-registration hook definition."
  type = object({
    type                = optional(string, "none")
    command             = optional(string, "")
    manual_prerequisite = optional(bool, false)
    notes               = optional(string, "")
  })
  default = {}
}

variable "iac" {
  description = "Demo-specific IaC hook definition."
  type = object({
    type    = optional(string, "none")
    command = optional(string, "")
    notes   = optional(string, "")
  })
  default = {}
}

variable "enable_registration" {
  type    = bool
  default = false
}

variable "registration_env" {
  description = "Environment variables passed to the registration hook (e.g. PROJECT_ENDPOINT, AZURE_CLIENT_ID)."
  type        = map(string)
  default     = {}
}

variable "enable_iac" {
  type    = bool
  default = false
}

variable "name_prefix" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "repo_root" {
  type = string
}

variable "acr_login_server" {
  type = string
}

variable "acr_name" {
  type = string
}

variable "container_app_environment_id" {
  type = string
}

variable "identity_id" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
