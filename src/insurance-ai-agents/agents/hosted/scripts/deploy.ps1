<#
.SYNOPSIS
  Deploy the insurance claims orchestrator to Azure AI Foundry as a hosted agent
  using direct-code deployment (zip upload + Foundry remote build - no Docker/ACR).

.DESCRIPTION
  Builds the flat code zip, then creates the agent (or a new version if it already
  exists) via the Foundry direct-code REST API, and polls until the version is active.

.EXAMPLE
  ./deploy.ps1
  ./deploy.ps1 -ProjectEndpoint "https://<acct>.services.ai.azure.com/api/projects/<proj>" -AgentName insurance-claims-orchestrator
#>
param(
  [string]$ProjectEndpoint = "https://ai-account-kzrzuypevlok4.services.ai.azure.com/api/projects/ai-project-ins-ai-foundry",
  [string]$AgentName = "insurance-claims-orchestrator",
  [string]$ApiVersion = "2025-11-15-preview",
  [string]$AppInsightsName = "appi-kzrzuypevlok4",
  [string]$AppInsightsResourceGroup = "rg-ins-ai-foundry",
  [string]$SecondaryAppInsightsName = "ins-ai-demo-ai-jii435hjlwyyc",
  [string]$SecondaryAppInsightsResourceGroup = "rg-insurance-ai-demo",
  [switch]$NoTracing
)
$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$hostedDir = Split-Path -Parent $here
$metadata = Join-Path $hostedDir ".foundry\direct-code\metadata.json"
$zip = Join-Path $env:TEMP "insurance-agent-code.zip"
$features = "CodeAgents=V1Preview,HostedAgents=V1Preview"

# Resolve az (it may not be on PATH).
$az = (Get-Command az -ErrorAction SilentlyContinue).Source
if (-not $az) { $az = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd" }

# Inject Application Insights tracing. The connection string is fetched at deploy time
# and merged into a temp metadata file - it is NEVER committed. With it set, the MAF
# orchestrator (configure_azure_monitor) and the agent server export OTel traces.
$effMetadata = $metadata
if (-not $NoTracing) {
  $conn = & $az resource show -g $AppInsightsResourceGroup -n $AppInsightsName --resource-type "microsoft.insights/components" --query "properties.ConnectionString" -o tsv 2>$null
  if ($conn) {
    $m = Get-Content $metadata -Raw | ConvertFrom-Json
    $m.definition.environment_variables | Add-Member -NotePropertyName APPLICATIONINSIGHTS_CONNECTION_STRING -NotePropertyValue $conn -Force
    Write-Host "Tracing: injected App Insights connection from '$AppInsightsName'."
    # Dual-export: also send the same agent traces to the demo's shared App Insights,
    # so the waterfall is visible BOTH in the Foundry Tracing tab and the main workspace.
    if ($SecondaryAppInsightsName) {
      $conn2 = & $az resource show -g $SecondaryAppInsightsResourceGroup -n $SecondaryAppInsightsName --resource-type "microsoft.insights/components" --query "properties.ConnectionString" -o tsv 2>$null
      if ($conn2 -and $conn2 -ne $conn) {
        $m.definition.environment_variables | Add-Member -NotePropertyName APPLICATIONINSIGHTS_CONNECTION_STRING_SECONDARY -NotePropertyValue $conn2 -Force
        Write-Host "Tracing: dual-export also to '$SecondaryAppInsightsName'."
      } else {
        Write-Host "Tracing: secondary App Insights '$SecondaryAppInsightsName' not found or same as primary; single-export."
      }
    }
    $effMetadata = Join-Path $env:TEMP "insurance-agent-metadata.json"
    $m | ConvertTo-Json -Depth 10 | Set-Content $effMetadata -Encoding utf8
  } else {
    Write-Host "Tracing: App Insights '$AppInsightsName' not found; deploying without tracing."
  }
}

Write-Host "Building code zip..."
& python (Join-Path $here "build_package.py") $zip | Out-Null
$sha = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()
Write-Host "  zip=$zip sha256=$sha"

$tok = & $az account get-access-token --resource https://ai.azure.com --query accessToken -o tsv
$auth = "Authorization: Bearer $tok"

# Create the agent if missing, else add a new version.
$exists = curl.exe -s -o $env:TEMP\__get.json -w "%{http_code}" -X GET "$ProjectEndpoint/agents/$AgentName`?api-version=$ApiVersion" -H $auth -H "Foundry-Features: $features"
if ($exists -eq "404") {
  Write-Host "Creating agent $AgentName..."
  $url = "$ProjectEndpoint/agents?api-version=$ApiVersion"
  $extra = @("-H", "x-ms-agent-name: $AgentName")
} else {
  Write-Host "Agent exists (HTTP $exists) - creating new version..."
  $url = "$ProjectEndpoint/agents/$AgentName/versions?api-version=$ApiVersion"
  $extra = @()
}

$code = curl.exe -s -o $env:TEMP\__create.json -w "%{http_code}" -X POST $url `
  -H $auth -H "Accept: application/json" -H "Foundry-Features: $features" `
  -H "x-ms-code-zip-sha256: $sha" @extra `
  -F "metadata=@$effMetadata;type=application/json" `
  -F "code=@$zip;type=application/zip;filename=$AgentName.zip"
Write-Host "POST -> HTTP $code"
if ($code -notmatch "^20") { Get-Content $env:TEMP\__create.json -Raw; throw "Create/version failed" }

# Derive the newest version from the versions list (robust across create vs create-version responses).
curl.exe -s -o "$env:TEMP\__vers.json" -X GET "$ProjectEndpoint/agents/$AgentName/versions`?api-version=$ApiVersion" -H $auth -H "Foundry-Features: $features" | Out-Null
$ver = ((Get-Content "$env:TEMP\__vers.json" -Raw | ConvertFrom-Json).data | ForEach-Object { [int]$_.version } | Measure-Object -Maximum).Maximum
Write-Host "Polling version $ver until active..."
for ($i = 0; $i -lt 24; $i++) {
  Start-Sleep -Seconds 15
  curl.exe -s -o "$env:TEMP\__ver.json" -X GET "$ProjectEndpoint/agents/$AgentName/versions/$ver`?api-version=$ApiVersion" -H $auth -H "Foundry-Features: $features" | Out-Null
  if (-not (Test-Path "$env:TEMP\__ver.json")) { continue }
  $st = (Get-Content "$env:TEMP\__ver.json" -Raw | ConvertFrom-Json).status
  Write-Host "  status=$st"
  if ($st -ne "creating") { break }
}
Write-Host "Done. Agent $AgentName version $ver"
Write-Host "Invoke endpoint: $ProjectEndpoint/agents/$AgentName/endpoint/protocols/invocations"
