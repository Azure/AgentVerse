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
  description = "Lowercase prefix for the Foundry (AI Services) account name (<= 18 chars — a 6-char random suffix is appended for global uniqueness and fast destroy/redeploy cycles)."
  validation {
    condition     = can(regex("^[a-z][a-z0-9]{0,17}$", var.foundry_account_name))
    error_message = "foundry_account_name must be lowercase alphanumeric, start with a letter, and be <= 18 chars (a 6-char suffix is appended; account names max out at 24)."
  }
}

variable "foundry_project_name" {
  type        = string
  description = "Foundry project name used to compose PROJECT_ENDPOINT for the local .env sync. The project itself is still created outside Terraform — see the closing note in main.tf."
  default     = "prodsched"
}

# ---- Chat model (monitor / orchestrator / dispatcher) --------------------------

# Model/version pairs age out: Azure refuses new deployments of models in
# "deprecating" state (gpt-4.1/2025-04-14 was refused on 2026-07-09 with
# ServiceModelDeprecating). Check what your region currently offers with:
#   az cognitiveservices model list -l <location> -o table
variable "model_deployment_name" {
  type        = string
  description = "Deployment name the app references (MODEL_DEPLOYMENT_NAME in .env)."
  default     = "gpt-5.1"
}

variable "model_name" {
  type        = string
  description = "Chat model to deploy."
  default     = "gpt-5.1"
}

variable "model_version" {
  type        = string
  description = "Chat model version."
  default     = "2025-11-13"
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
  default     = "2026-03-05"
}

variable "reasoning_model_capacity" {
  type        = number
  description = "Reasoning deployment capacity (thousands of tokens/min)."
  default     = 50
}

# ---- Web app (the hosted demo) ----------------------------------------------------

variable "hosting" {
  type        = string
  description = "Where to host the demo UI: 'containerapp' (default; expandable, own quota bucket), 'appservice' (zip deploy, needs App Service VM quota), or 'none' (skip hosting — stages 1-4 don't need it)."
  default     = "containerapp"
  validation {
    condition     = contains(["containerapp", "appservice", "none"], var.hosting)
    error_message = "hosting must be one of: containerapp, appservice, none."
  }
}

variable "webapp_location" {
  type        = string
  description = "Region for the hosting resources only (empty = same as location). Useful when the main region lacks hosting quota — e.g. App Service quota was 0 in eastus2 on a managed subscription while westus2 had capacity."
  default     = ""
}

variable "webapp_name" {
  type        = string
  description = "Globally-unique name for the hosted demo (App Service: <name>.azurewebsites.net; Container Apps: also seeds the ACR name)."
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
