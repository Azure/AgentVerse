"""Configure APIM diagnostic settings to send logs to Log Analytics."""
import os, requests, sys

token = os.environ.get("AZ_TOKEN", "")
if not token:
    print("Error: AZ_TOKEN not set")
    sys.exit(1)

sub = "d9615658-8170-4490-8dd7-12e5d5f988ed"
rg = "rg-insurance-ai-demo"
apim = "ins-ai-demo-apim-jii435hjlwyyc"
law = "ins-ai-demo-law-jii435hjlwyyc"

apim_id = f"/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.ApiManagement/service/{apim}"
law_id = f"/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.OperationalInsights/workspaces/{law}"

# Create diagnostic settings
url = f"https://management.azure.com{apim_id}/providers/Microsoft.Insights/diagnosticSettings/apim-audit?api-version=2021-05-01-preview"

body = {
    "properties": {
        "workspaceId": law_id,
        "logs": [
            {"category": "GatewayLogs", "enabled": True, "retentionPolicy": {"enabled": False, "days": 0}}
        ],
        "metrics": [
            {"category": "AllMetrics", "enabled": True, "retentionPolicy": {"enabled": False, "days": 0}}
        ]
    }
}

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
r = requests.put(url, json=body, headers=headers)
print(f"Diagnostic settings: {r.status_code}")
if not r.ok:
    print(f"Error: {r.text[:300]}")
else:
    print("APIM logs → Log Analytics configured")

# Also enable API-level diagnostics for detailed request/response logging
diag_url = f"https://management.azure.com{apim_id}/apis/azure-openai-api/diagnostics/applicationinsights?api-version=2023-09-01-preview"
diag_body = {
    "properties": {
        "loggerId": f"{apim_id}/loggers/azuremonitor",
        "sampling": {"samplingType": "fixed", "percentage": 100},
        "alwaysLog": "allErrors",
        "logClientIp": True,
        "verbosity": "information",
        "httpCorrelationProtocol": "W3C"
    }
}
r2 = requests.put(diag_url, json=diag_body, headers=headers)
print(f"API diagnostics: {r2.status_code}")
if not r2.ok:
    print(f"(non-critical) {r2.text[:200]}")
