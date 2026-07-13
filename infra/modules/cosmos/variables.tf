variable "name_prefix" {
  type = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "identity_principal_id" {
  description = "Principal id of the identity granted Cosmos data-plane access (keyless)."
  type        = string
}

variable "database_name" {
  type    = string
  default = "insurance-claims"
}

variable "container_name" {
  type    = string
  default = "claims"
}

variable "log_analytics_workspace_id" {
  description = "Shared Log Analytics workspace id for diagnostic settings."
  type        = string
  default     = ""
}
