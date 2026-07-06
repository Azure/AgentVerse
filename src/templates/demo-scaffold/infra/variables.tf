variable "resource_group" {
  type        = string
  description = "Resource group to create/use for this demo."
}

variable "location" {
  type        = string
  description = "Azure region. Pick one with quota for your models (e.g. eastus2)."
  default     = "eastus2"
}

variable "foundry_account_name" {
  type        = string
  description = "Globally-unique, lowercase Foundry (AI Services) account name (<= 24 chars)."
}

variable "model_deployment_name" {
  type        = string
  description = "Deployment name the app references (MODEL_DEPLOYMENT_NAME in .env)."
  default     = "gpt-4.1"
}

variable "model_name" {
  type        = string
  description = "Model to deploy."
  default     = "gpt-4.1"
}

variable "model_version" {
  type        = string
  description = "Model version."
  default     = "2025-04-14"
}

variable "model_capacity" {
  type        = number
  description = "Deployment capacity (thousands of tokens/min)."
  default     = 50
}
