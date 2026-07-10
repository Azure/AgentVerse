variable "name_prefix" {
  type = string
}

variable "location" {
  description = "Region for the shared AIServices account and its model deployments."
  type        = string
}

variable "resource_group_name" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "identity_principal_id" {
  description = "Principal id of the shared user-assigned identity used by the demo container apps (granted inference + agent roles)."
  type        = string
}

variable "deployer_object_id" {
  description = "Object id of the identity running Terraform (granted Azure AI Developer so agent bootstrap can create agents)."
  type        = string
}

# ---------------------------------------------------------------------------
# Model deployment capacities (thousands of tokens/min for chat models). Kept
# modest by default so the two demos fit comfortably within GlobalStandard quota.
# ---------------------------------------------------------------------------

variable "gpt41_capacity" {
  type    = number
  default = 20
}

variable "gpt_image_2_capacity" {
  type    = number
  default = 1
}

variable "gpt_5_4_mini_capacity" {
  type    = number
  default = 30
}

variable "gpt_realtime_mini_capacity" {
  type    = number
  default = 1
}

variable "gpt_5_1_capacity" {
  type    = number
  default = 20
}

variable "gpt_5_4_capacity" {
  type    = number
  default = 20
}

variable "bing_connection_name" {
  description = "Name of the Bing grounding project connection (must match the demo's BING_CONNECTION_NAME)."
  type        = string
  default     = "bing-grounding"
}
