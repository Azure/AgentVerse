#!/usr/bin/env bash
# ============================================================================
# Deploy Infrastructure — Insurance AI Demo
# ============================================================================
# Deploys all Azure resources via Bicep
# Usage: ./scripts/deploy-infra.sh <resource-group> <location>
# ============================================================================

set -euo pipefail

RESOURCE_GROUP="${1:-rg-insurance-ai-demo}"
LOCATION="${2:-swedencentral}"

echo "🏗️  Insurance AI Demo — Infrastructure Deployment"
echo "   Resource Group: ${RESOURCE_GROUP}"
echo "   Location: ${LOCATION}"
echo ""

# Create resource group
echo "📦 Creating resource group..."
az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}" --output none

# Deploy Bicep template
echo "🚀 Deploying infrastructure (this may take 30+ minutes for APIM)..."
az deployment group create \
    --resource-group "${RESOURCE_GROUP}" \
    --template-file infra/main.bicep \
    --parameters location="${LOCATION}" \
    --output json \
    --query "properties.outputs" \
    > .azure-outputs.json

echo ""
echo "✅ Infrastructure deployed!"
echo ""
echo "📋 Outputs:"
cat .azure-outputs.json | python -m json.tool

# Extract outputs for .env
OPENAI_ENDPOINT=$(cat .azure-outputs.json | python -c "import json,sys; print(json.load(sys.stdin)['openAiEndpoint']['value'])")
ACR_NAME=$(cat .azure-outputs.json | python -c "import json,sys; print(json.load(sys.stdin)['acrName']['value'])")
APIM_URL=$(cat .azure-outputs.json | python -c "import json,sys; print(json.load(sys.stdin)['apimGatewayUrl']['value'])")

echo ""
echo "📝 Creating .env file..."
cat > .env << EOF
AZURE_OPENAI_ENDPOINT=${OPENAI_ENDPOINT}
AZURE_OPENAI_DEPLOYMENT=gpt-5.4-mini
APIM_GATEWAY_URL=${APIM_URL}
ACR_NAME=${ACR_NAME}
FRONTEND_URL=http://localhost:5173
EOF

echo "✅ .env file created"
echo ""
echo "🎯 Next steps:"
echo "   1. Run 'az login' if not already authenticated"
echo "   2. Start the backend: cd backend && pip install -r requirements.txt && python main.py"
echo "   3. Start the dashboard: cd dashboard && npm install && npm run dev"
echo "   4. Run demo scenarios: python scripts/run_demo.py"
