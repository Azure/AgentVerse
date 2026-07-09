variable "name_prefix" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "repo_root" {
  type = string
}

variable "image_context" {
  description = "Portal build context, relative to repo root."
  type        = string
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

variable "cpu" {
  type    = number
  default = 0.5
}

variable "memory" {
  type    = string
  default = "1Gi"
}

variable "demo_web_urls" {
  description = "Map of demo_id => public web URL used as iframe targets."
  type        = map(string)
  default     = {}
}

variable "tags" {
  type    = map(string)
  default = {}
}
