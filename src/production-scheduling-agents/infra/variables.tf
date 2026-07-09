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

# ---- Chat model (monitor / orchestrator / dispatcher) --------------------------

variable "model_deployment_name" {
  type        = string
  description = "Deployment name the app references (MODEL_DEPLOYMENT_NAME in .env)."
  default     = "gpt-4.1"
}

variable "model_name" {
  type        = string
  description = "Chat model to deploy."
  default     = "gpt-4.1"
}

variable "model_version" {
  type        = string
  description = "Chat model version."
  default     = "2025-04-14"
}

variable "model_capacity" {
  type        = number
  description = "Chat deployment capacity (thousands of tokens/min)."
  default     = 50
}

# ---- Reasoning model (scenario-simulator) ---------------------------------------

variable "reasoning_model_deployment_name" {
  type        = string
  description = "Deployment name for the reasoning model (REASONING_MODEL_DEPLOYMENT_NAME in .env)."
  default     = "gpt-5.4"
}

variable "reasoning_model_name" {
  type        = string
  description = "Reasoning model to deploy (used for schedule trade-off analysis)."
  default     = "gpt-5.4"
}

variable "reasoning_model_version" {
  type        = string
  description = "Reasoning model version."
  default     = "2026-01-15"
}

variable "reasoning_model_capacity" {
  type        = number
  description = "Reasoning deployment capacity (thousands of tokens/min)."
  default     = 50
}

# ---- Web app (the hosted demo) ----------------------------------------------------

variable "webapp_name" {
  type        = string
  description = "Globally-unique App Service name (becomes <name>.azurewebsites.net)."
}

variable "app_service_sku" {
  type        = string
  description = "App Service plan SKU. B1 is plenty for a demo."
  default     = "B1"
}

variable "webapp_project_endpoint" {
  type        = string
  description = "Foundry PROJECT_ENDPOINT for live agents. Empty = replay mode (default, deterministic demo)."
  default     = ""
}
