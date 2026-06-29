# ============================================================================
# Deploy Infrastructure — Insurance AI Demo (PowerShell)
# ============================================================================
# Usage: .\scripts\deploy-infra.ps1 [-ResourceGroup rg-name] [-Location region]
# ============================================================================

param(
    [string]$ResourceGroup = "rg-insurance-ai-demo",
    [string]$Location = "swedencentral"
)

$ErrorActionPreference = "Stop"

Write-Host "`n🏗️  Insurance AI Demo — Infrastructure Deployment" -ForegroundColor Cyan
Write-Host "   Resource Group: $ResourceGroup"
Write-Host "   Location: $Location"
Write-Host ""

# Create resource group
Write-Host "📦 Creating resource group..." -ForegroundColor Yellow
az group create --name $ResourceGroup --location $Location --output none

# Deploy Bicep template
Write-Host "🚀 Deploying infrastructure (this may take 30+ minutes for APIM)..." -ForegroundColor Yellow
$outputs = az deployment group create `
    --resource-group $ResourceGroup `
    --template-file infra/main.bicep `
    --parameters location=$Location `
    --query "properties.outputs" `
    --output json | ConvertFrom-Json

Write-Host "`n✅ Infrastructure deployed!" -ForegroundColor Green

# Extract outputs
$openAiEndpoint = $outputs.openAiEndpoint.value
$acrName = $outputs.acrName.value
$apimUrl = $outputs.apimGatewayUrl.value
$acrLoginServer = $outputs.acrLoginServer.value
$appInsightsKey = $outputs.appInsightsInstrumentationKey.value

Write-Host "`n📋 Key Outputs:" -ForegroundColor Cyan
Write-Host "   OpenAI Endpoint:  $openAiEndpoint"
Write-Host "   APIM Gateway:     $apimUrl"
Write-Host "   ACR:              $acrLoginServer"

# Create .env
$envContent = @"
AZURE_OPENAI_ENDPOINT=$openAiEndpoint
AZURE_OPENAI_DEPLOYMENT=gpt-5.4-mini
APIM_GATEWAY_URL=$apimUrl
ACR_NAME=$acrName
FRONTEND_URL=http://localhost:5173
APPINSIGHTS_INSTRUMENTATIONKEY=$appInsightsKey
"@

Set-Content -Path ".env" -Value $envContent
Write-Host "`n📝 .env file created" -ForegroundColor Green

Write-Host "`n🎯 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Run 'az login' if not already authenticated"
Write-Host "   2. Start backend: cd backend; pip install -r requirements.txt; python main.py"
Write-Host "   3. Start dashboard: cd dashboard; npm install; npm run dev"
Write-Host "   4. Run demo: python scripts/run_demo.py"
