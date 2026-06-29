# ============================================================================
# One-command full deploy — Insurance AI (Helix) whitelabel demo
# ============================================================================
# Provisions infra (Bicep) + deploys backend (Container Apps via ACR build) +
# builds & deploys dashboard (Static Web Apps). No local Docker required.
#
#   az login   (once)
#   .\scripts\deploy.ps1 -ResourceGroup rg-helix-demo -Location swedencentral
#
# Brand:  BRAND_NAME defaults to "Helix Insurance"; pass -BrandName "X" to skin.
# ============================================================================
param(
    [string]$ResourceGroup = "rg-insurance-ai-demo",
    [string]$Location = "swedencentral",
    [string]$BrandName = "Helix Insurance"
)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Write-Host "`nInsurance AI - full deploy => $ResourceGroup ($Location)" -ForegroundColor Cyan

# 1) Infra ------------------------------------------------------------------
az group create -n $ResourceGroup -l $Location -o none
Write-Host "Provisioning infra (Bicep, ~30 min first run for APIM)..." -ForegroundColor Yellow
$o = az deployment group create -g $ResourceGroup --template-file "$root/infra/main.bicep" `
    --parameters location=$Location --query properties.outputs -o json | ConvertFrom-Json

$acr = $o.acrName.value
$openai = $o.openAiEndpoint.value
$apim = $o.apimGatewayUrl.value
$cosmos = $o.cosmosEndpoint.value
$swa = $o.staticWebAppName.value
$caeId = $o.containerAppEnvId.value
$ai = $o.appInsightsConnectionString.value

# 2) Backend -> ACR build + Container App -----------------------------------
Write-Host "Building backend image in ACR..." -ForegroundColor Yellow
az acr build -r $acr -t "insurance-ai-backend:latest" -f "$root/backend/Dockerfile" $root -o none

$be = "insurance-ai-backend"
az containerapp show -n $be -g $ResourceGroup -o none 2>$null; $ok = $?
$envVars = @(
    "AZURE_OPENAI_ENDPOINT=$openai",
    "AZURE_OPENAI_DEPLOYMENT=gpt-5.4-mini",
    "USE_MAF_ORCHESTRATOR=true",
    "COSMOS_ENDPOINT=$cosmos",
    "APPLICATIONINSIGHTS_CONNECTION_STRING=$ai",
    "BRAND_NAME=$BrandName",
    "FRONTEND_URL=*"
)
if (-not $ok) {
    az containerapp create -n $be -g $ResourceGroup --environment $caeId `
        --image "$acr.azurecr.io/insurance-ai-backend:latest" --registry-server "$acr.azurecr.io" `
        --target-port 8000 --ingress external --min-replicas 1 --cpu 1 --memory 2Gi `
        --env-vars $envVars -o none
} else {
    az containerapp update -n $be -g $ResourceGroup --image "$acr.azurecr.io/insurance-ai-backend:latest" --set-env-vars $envVars -o none
}
$beUrl = "https://" + (az containerapp show -n $be -g $ResourceGroup --query properties.configuration.ingress.fqdn -o tsv)
Write-Host "Backend: $beUrl" -ForegroundColor Green

# 3) Dashboard -> build + SWA deploy ----------------------------------------
Write-Host "Building dashboard (VITE_API_URL=$beUrl)..." -ForegroundColor Yellow
Push-Location "$root/dashboard"
$env:VITE_API_URL = $beUrl
npm ci; npm run build
$tok = az staticwebapp secrets list -n $swa --query properties.apiKey -o tsv
npx --yes @azure/static-web-apps-cli deploy ./dist --deployment-token $tok --env production
Pop-Location

$swaUrl = "https://" + (az staticwebapp show -n $swa -g $ResourceGroup --query defaultHostname -o tsv)
Write-Host "`nDone. App: $swaUrl  |  API: $beUrl" -ForegroundColor Green
