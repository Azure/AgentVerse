variable "location" {
  description = "Azure region for the demo resources (needs gpt-4.1 + Azure AI Search)."
  type        = string
  default     = "swedencentral"
}

variable "name_prefix" {
  description = "Short prefix for resource names."
  type        = string
  default     = "signaltoservice"
}

variable "model_name" {
  description = "Chat model used by the three prompt agents."
  type        = string
  default     = "gpt-4.1"
}

variable "model_version" {
  description = "Chat model version."
  type        = string
  default     = "2025-04-14"
}

variable "model_capacity" {
  description = "GlobalStandard capacity (thousands of TPM) for the chat deployment."
  type        = number
  default     = 20
}

variable "search_sku" {
  description = "Azure AI Search SKU (basic is enough for the SOP index)."
  type        = string
  default     = "basic"
}

variable "seed_search_index" {
  description = "Run scripts/seed_search_index.py after apply to create + fill the SOP index. Requires Python and the app deps on the machine running terraform."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags applied to all resources."
  type        = map(string)
  default = {
    demo            = "signal-to-service"
    SecurityControl = "Ignore"
  }
}
