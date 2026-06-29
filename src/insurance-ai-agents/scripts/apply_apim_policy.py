"""Apply APIM AI Gateway policy via REST API."""
import os, requests, json, sys

token = os.environ.get("AZ_TOKEN", "")
if not token:
    print("Error: AZ_TOKEN environment variable not set")
    sys.exit(1)

sub = "d9615658-8170-4490-8dd7-12e5d5f988ed"
rg = "rg-insurance-ai-demo"
apim = "ins-ai-demo-apim-jii435hjlwyyc"

policy_xml = """<policies>
  <inbound>
    <base />
    <authentication-managed-identity resource="https://cognitiveservices.azure.com" />
    <set-header name="X-Gateway-Source" exists-action="override">
      <value>insurance-ai-gateway</value>
    </set-header>
    <azure-openai-token-limit
        tokens-per-minute="50000"
        counter-key="@(context.Subscription.Id)"
        estimate-prompt-tokens="true"
        tokens-consumed-header-name="x-tokens-consumed"
        remaining-tokens-header-name="x-tokens-remaining" />
    <set-backend-service backend-id="openai-backend" />
    <azure-openai-emit-token-metric namespace="insurance-ai-gateway">
      <dimension name="Agent" value="@(context.Request.Headers.GetValueOrDefault(&quot;X-Agent-Id&quot;, &quot;unknown&quot;))" />
      <dimension name="Subscription" value="@(context.Subscription.Id)" />
    </azure-openai-emit-token-metric>
  </inbound>
  <backend>
    <forward-request timeout="120" />
  </backend>
  <outbound>
    <base />
  </outbound>
  <on-error>
    <base />
  </on-error>
</policies>"""

url = (
    f"https://management.azure.com/subscriptions/{sub}/resourceGroups/{rg}"
    f"/providers/Microsoft.ApiManagement/service/{apim}"
    f"/apis/azure-openai-api/policies/policy?api-version=2023-09-01-preview"
)

body = {"properties": {"format": "xml", "value": policy_xml}}
headers = {"Authorization": f"Bearer {token}", "If-Match": "*", "Content-Type": "application/json"}

r = requests.put(url, json=body, headers=headers)
print(f"Status: {r.status_code}")
if r.ok:
    print(f"Policy applied successfully: {r.json().get('name', 'policy')}")
else:
    print(f"Error: {r.text[:500]}")
