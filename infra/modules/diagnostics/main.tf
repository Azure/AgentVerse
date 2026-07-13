# ---------------------------------------------------------------------------
# Reusable diagnostic setting: streams every log category and metric a resource
# supports to the shared Log Analytics workspace (Azure Monitor). Categories are
# discovered per-resource via the diagnostic-categories data source, so we never
# hardcode "allLogs" (unsupported on some resource types) and never enumerate
# categories that a given SKU/resource does not expose.
# ---------------------------------------------------------------------------

variable "name" {
  type    = string
  default = "to-law"
}

variable "target_resource_id" {
  type = string
}

variable "log_analytics_workspace_id" {
  type = string
}

# The Container Apps Environment already streams console/system logs to the
# workspace via its built-in destination, so callers can disable the log
# categories here (metrics only) to avoid duplicate log ingestion.
variable "logs_enabled" {
  type    = bool
  default = true
}

variable "metrics_enabled" {
  type    = bool
  default = true
}

data "azurerm_monitor_diagnostic_categories" "this" {
  resource_id = var.target_resource_id
}

resource "azurerm_monitor_diagnostic_setting" "this" {
  name                       = var.name
  target_resource_id         = var.target_resource_id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  dynamic "enabled_log" {
    for_each = var.logs_enabled ? toset(data.azurerm_monitor_diagnostic_categories.this.log_category_types) : toset([])
    content {
      category = enabled_log.value
    }
  }

  dynamic "metric" {
    for_each = var.metrics_enabled ? toset(data.azurerm_monitor_diagnostic_categories.this.metrics) : toset([])
    content {
      category = metric.value
      enabled  = true
    }
  }
}
