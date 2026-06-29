// ============================================================================
// Insurance AI Agents Demo - Main Infrastructure
// ============================================================================
// Deploys: Azure OpenAI, APIM, Content Safety, ACR, Container Apps, 
//          Static Web Apps, Application Insights, AI Foundry Project
// ============================================================================

targetScope = 'resourceGroup'

@description('Base name for all resources')
param baseName string = 'ins-ai-demo'

@description('Azure region for resources')
param location string = resourceGroup().location

@description('Primary chat model deployment name (used by all reasoning agents)')
param chatModelName string = 'gpt-5.4-mini'

@description('Primary chat model version')
param chatModelVersion string = '2026-03-17'

@description('Realtime voice model deployment name (gpt-realtime-mini for cost-optimized voice)')
param voiceModelName string = 'gpt-realtime-mini'

@description('Realtime voice model version')
param voiceModelVersion string = '2025-12-15'

@description('APIM publisher name')
param apimPublisherName string = 'Insurance AI Demo'

@description('APIM publisher email')
param apimPublisherEmail string = 'admin@insurance-ai-demo.com'

@description('Object ID of the principal (user or service principal) that should get Cosmos DB data-plane access. Leave empty to skip the role assignment.')
param cosmosDataPlanePrincipalId string = ''

// ============================================================================
// Variables
// ============================================================================

var uniqueSuffix = uniqueString(resourceGroup().id)
var openAiName = '${baseName}-aoai-${uniqueSuffix}'
var apimName = '${baseName}-apim-${uniqueSuffix}'
var contentSafetyName = '${baseName}-safety-${uniqueSuffix}'
var acrName = replace('${baseName}acr${uniqueSuffix}', '-', '')
var containerAppEnvName = '${baseName}-cae-${uniqueSuffix}'
var staticWebAppName = '${baseName}-swa-${uniqueSuffix}'
var appInsightsName = '${baseName}-ai-${uniqueSuffix}'
var logAnalyticsName = '${baseName}-law-${uniqueSuffix}'
var aiServicesName = '${baseName}-ais-${uniqueSuffix}'
var cosmosName = '${baseName}-cosmos-${uniqueSuffix}'

// ============================================================================
// Monitoring: Log Analytics + Application Insights
// ============================================================================

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    // Cost optimization: 30d -> 14d retention (saves ~50% on retention charges).
    // Bump to 30+ when promoted to production with regulatory retention needs.
    retentionInDays: 14
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    // Cost optimization: ingest only 10% of telemetry (saves ~90% on ingestion
    // for high-volume scenarios). Bump back to 100 when investigating issues.
    SamplingPercentage: 10
  }
}

// ============================================================================
// Azure OpenAI
// ============================================================================

resource openAi 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: openAiName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: openAiName
    publicNetworkAccess: 'Enabled'
  }
}

// ============================================================================
// Azure OpenAI deployments
// ============================================================================
// We deploy two models on the same OpenAI account:
//   1) chat model (gpt-5.4-mini) — used by Intake / Risk / Compliance agents
//   2) realtime voice model (gpt-realtime-mini) — used by the voice channel
// GlobalStandard SKU is pure PayGo: capacity sets the TPM cap but billing is
// per-token used. No reserved capacity charge.

resource chatDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openAi
  name: chatModelName
  sku: {
    name: 'GlobalStandard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: chatModelName
      version: chatModelVersion
    }
  }
}

resource voiceDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openAi
  name: voiceModelName
  sku: {
    name: 'GlobalStandard'
    capacity: 1
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: voiceModelName
      version: voiceModelVersion
    }
  }
  dependsOn: [chatDeployment]
}

// NOTE: text-embedding-ada-002 deployment was removed (no code path used it).
// If RAG over policy documents is added later, deploy text-embedding-3-small
// (cheaper and higher quality than ada-002) on demand.

// ============================================================================
// Azure AI Services (Foundry-compatible)
// ============================================================================

resource aiServices 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: aiServicesName
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: aiServicesName
    publicNetworkAccess: 'Enabled'
  }
}

// ============================================================================
// Azure Content Safety
// ============================================================================

resource contentSafety 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: contentSafetyName
  location: location
  kind: 'ContentSafety'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: contentSafetyName
    publicNetworkAccess: 'Enabled'
  }
}

// ============================================================================
// Azure Container Registry
// ============================================================================

resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// ============================================================================
// Azure API Management (AI Gateway)
// ============================================================================

resource apim 'Microsoft.ApiManagement/service@2023-09-01-preview' = {
  name: apimName
  location: location
  sku: {
    // Cost optimization: BasicV2 (~150eur/mo) instead of StandardV2 (~600eur/mo).
    // BasicV2 fully supports the AI Gateway policy suite (llm-content-safety,
    // azure-openai-token-limit, azure-openai-emit-token-metric, managed-identity
    // auth) which is what this demo showcases. Promote to StandardV2 for
    // production traffic (regional HA, more throughput, custom domains).
    name: 'BasicV2'
    capacity: 1
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    publisherName: apimPublisherName
    publisherEmail: apimPublisherEmail
  }
}

// ============================================================================
// APIM → Azure OpenAI Backend
// ============================================================================

resource apimOpenAiBackend 'Microsoft.ApiManagement/service/backends@2023-09-01-preview' = {
  parent: apim
  name: 'openai-backend'
  properties: {
    protocol: 'http'
    url: '${openAi.properties.endpoint}openai'
    tls: {
      validateCertificateChain: true
      validateCertificateName: true
    }
  }
}

// ============================================================================
// APIM → Content Safety Backend
// ============================================================================

resource apimContentSafetyBackend 'Microsoft.ApiManagement/service/backends@2023-09-01-preview' = {
  parent: apim
  name: 'contentsafety-backend'
  properties: {
    protocol: 'http'
    url: '${contentSafety.properties.endpoint}'
    tls: {
      validateCertificateChain: true
      validateCertificateName: true
    }
  }
}

// ============================================================================
// APIM API: Azure OpenAI passthrough — agents call /openai/* on the gateway
// ============================================================================

resource apimOpenAiApi 'Microsoft.ApiManagement/service/apis@2023-09-01-preview' = {
  parent: apim
  name: 'azure-openai'
  properties: {
    displayName: 'Azure OpenAI (governed)'
    description: 'AI Gateway in front of Azure OpenAI: managed-identity auth, content safety, token rate-limit, audit log, token metrics.'
    path: 'openai-gov'
    protocols: ['https']
    serviceUrl: '${openAi.properties.endpoint}openai'
    subscriptionRequired: true
    apiType: 'http'
  }
}

// Single passthrough operation matching every Azure OpenAI route (deployments/{id}/chat/completions, etc.)
resource apimOpenAiOperation 'Microsoft.ApiManagement/service/apis/operations@2023-09-01-preview' = {
  parent: apimOpenAiApi
  name: 'openai-passthrough'
  properties: {
    displayName: 'Azure OpenAI passthrough'
    method: 'POST'
    urlTemplate: '/*'
  }
}

// Apply the AI Gateway policy XML (loaded from infra/apim-policy.xml)
resource apimOpenAiPolicy 'Microsoft.ApiManagement/service/apis/policies@2023-09-01-preview' = {
  parent: apimOpenAiApi
  name: 'policy'
  properties: {
    format: 'rawxml'
    value: loadTextContent('apim-policy.xml')
  }
}

// One subscription per agent → token-limit & metrics are sliced per agent
resource apimAgentProduct 'Microsoft.ApiManagement/service/products@2023-09-01-preview' = {
  parent: apim
  name: 'insurance-agents'
  properties: {
    displayName: 'Insurance AI Agents'
    description: 'Product that groups subscriptions for the multi-agent pipeline (intake, risk, compliance, orchestrator).'
    state: 'published'
    subscriptionRequired: true
    approvalRequired: false
  }
}

resource apimAgentProductApi 'Microsoft.ApiManagement/service/products/apis@2023-09-01-preview' = {
  parent: apimAgentProduct
  name: apimOpenAiApi.name
}

resource apimSubscriptionIntake 'Microsoft.ApiManagement/service/subscriptions@2023-09-01-preview' = {
  parent: apim
  name: 'sub-claims-intake'
  properties: {
    displayName: 'Claims Intake Agent'
    scope: '/products/${apimAgentProduct.id}'
    state: 'active'
  }
}

resource apimSubscriptionRisk 'Microsoft.ApiManagement/service/subscriptions@2023-09-01-preview' = {
  parent: apim
  name: 'sub-risk-assessment'
  properties: {
    displayName: 'Risk & Fraud Agent'
    scope: '/products/${apimAgentProduct.id}'
    state: 'active'
  }
}

resource apimSubscriptionCompliance 'Microsoft.ApiManagement/service/subscriptions@2023-09-01-preview' = {
  parent: apim
  name: 'sub-compliance'
  properties: {
    displayName: 'Compliance Agent'
    scope: '/products/${apimAgentProduct.id}'
    state: 'active'
  }
}

// ============================================================================
// RBAC: APIM → Cognitive Services User on Azure OpenAI
// ============================================================================

@description('Cognitive Services User role')
var cognitiveServicesUserRole = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  'a97b65f3-24c7-4388-baec-2e87135dc908'
)

resource apimOpenAiRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: openAi
  name: guid(apim.id, openAi.id, cognitiveServicesUserRole)
  properties: {
    roleDefinitionId: cognitiveServicesUserRole
    principalId: apim.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource apimContentSafetyRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: contentSafety
  name: guid(apim.id, contentSafety.id, cognitiveServicesUserRole)
  properties: {
    roleDefinitionId: cognitiveServicesUserRole
    principalId: apim.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// ============================================================================
// Container Apps Environment (for backend API)
// ============================================================================

resource containerAppEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerAppEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// ============================================================================
// Static Web App (Dashboard) — deployed to westeurope (not available in all regions)
// ============================================================================

resource staticWebApp 'Microsoft.Web/staticSites@2023-12-01' = {
  name: staticWebAppName
  location: 'westeurope'
  sku: {
    name: 'Free'
    tier: 'Free'
  }
  properties: {}
}

// ============================================================================
// Cosmos DB (NoSQL) - persistencia de siniestros procesados
// ============================================================================
// Container particionado por /customer_id (alta cardinalidad, query pattern
// dominante: "siniestros del cliente X"). Modo serverless para minimizar coste
// en demo. AAD-only: deshabilitamos las claves locales y usamos data-plane RBAC.

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: cosmosName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
      }
    ]
    capabilities: [
      { name: 'EnableServerless' }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource cosmosDb 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: cosmos
  name: 'insurance-claims'
  properties: {
    resource: {
      id: 'insurance-claims'
    }
  }
}

resource cosmosClaimsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: cosmosDb
  name: 'claims'
  properties: {
    resource: {
      id: 'claims'
      partitionKey: {
        paths: ['/customer_id']
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          { path: '/*' }
        ]
        excludedPaths: [
          { path: '/_etag/?' }
        ]
      }
      defaultTtl: -1
    }
  }
}

// Built-in Cosmos DB Data Contributor (data-plane RBAC, NOT ARM RBAC)
var cosmosDataContributorRoleId = '${cosmos.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'

resource cosmosDataPlaneRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = if (!empty(cosmosDataPlanePrincipalId)) {
  parent: cosmos
  name: guid(cosmos.id, cosmosDataPlanePrincipalId, 'data-contributor')
  properties: {
    roleDefinitionId: cosmosDataContributorRoleId
    principalId: cosmosDataPlanePrincipalId
    scope: cosmos.id
  }
}

// ============================================================================
// Outputs
// ============================================================================

output openAiEndpoint string = openAi.properties.endpoint
output openAiName string = openAi.name
output chatDeploymentName string = chatDeployment.name
output voiceDeploymentName string = voiceDeployment.name
output aiServicesEndpoint string = aiServices.properties.endpoint
output aiServicesName string = aiServices.name
output apimGatewayUrl string = apim.properties.gatewayUrl
output apimName string = apim.name
output acrLoginServer string = acr.properties.loginServer
output acrName string = acr.name
output contentSafetyEndpoint string = contentSafety.properties.endpoint
output containerAppEnvId string = containerAppEnv.id
output staticWebAppName string = staticWebApp.name
output appInsightsConnectionString string = appInsights.properties.ConnectionString
output appInsightsInstrumentationKey string = appInsights.properties.InstrumentationKey
output cosmosEndpoint string = cosmos.properties.documentEndpoint
output cosmosDatabaseName string = cosmosDb.name
output cosmosContainerName string = cosmosClaimsContainer.name
