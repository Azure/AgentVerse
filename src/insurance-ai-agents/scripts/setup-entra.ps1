# Configures the app registration `insurance-ai-demo-spa` for the demo:
# - Adds SPA platform with redirect URIs (localhost:5173 + Static Web App)
# - Defines the 2 App Roles (Customer.Submit, Operator.Review)
# - Assigns BOTH roles to the specified user (so they can switch in the demo)
#
# REQUIREMENTS:
#   az login --tenant <YOUR_TENANT> --scope https://graph.microsoft.com//.default
#   $TENANT_ID, $APP_OBJECT_ID and $USER_UPN are already set below.
#
# If your tenant has CAE enabled and returns TokenCreatedWithOutdatedPolicies:
#   az logout
#   az login --tenant 763b21d6-9a2e-4d90-88f9-d3c5cc8dba90

$ErrorActionPreference = 'Stop'

$AZ = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
$TENANT_ID = "763b21d6-9a2e-4d90-88f9-d3c5cc8dba90"
$APP_OBJECT_ID = "d3fd01da-0941-4bfc-b3c4-f8a63a19de91"
$APP_ID = "4e593597-088c-404c-984c-203259ff7dbe"
$USER_UPN = "admin@MngEnvMCAP135050.onmicrosoft.com"
$REDIRECT_URIS = @(
    "http://localhost:5173",
    "http://localhost:5173/"
)

# Stable IDs (same as app-roles.json) ----------------------------------
$ROLE_CUSTOMER_ID = "11111111-1111-1111-1111-111111111111"
$ROLE_OPERATOR_ID = "22222222-2222-2222-2222-222222222222"

function Get-GraphToken {
    & $AZ account get-access-token --resource-type ms-graph --query accessToken -o tsv
}

function Invoke-Graph {
    param([string]$Method, [string]$Path, $Body = $null)
    $token = Get-GraphToken
    $headers = @{ Authorization = "Bearer $token"; "Content-Type" = "application/json" }
    $uri = "https://graph.microsoft.com/v1.0$Path"
    if ($null -ne $Body) {
        $json = $Body | ConvertTo-Json -Depth 10
        return Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers -Body $json
    }
    return Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers
}

# 1) Update SPA redirect URIs + App Roles ---------------------------------
Write-Host "1/4  Configuring SPA redirect URIs and App Roles..." -ForegroundColor Cyan
$patchBody = @{
    spa      = @{ redirectUris = $REDIRECT_URIS }
    appRoles = @(
        @{
            id                 = $ROLE_CUSTOMER_ID
            allowedMemberTypes = @("User")
            description        = "Can create and view their own claims."
            displayName        = "Customer"
            isEnabled          = $true
            value              = "Customer.Submit"
        },
        @{
            id                 = $ROLE_OPERATOR_ID
            allowedMemberTypes = @("User")
            description        = "Can view all claims, the human review queue, statistics and the security/governance panel."
            displayName        = "Operator"
            isEnabled          = $true
            value              = "Operator.Review"
        }
    )
}
Invoke-Graph -Method PATCH -Path "/applications/$APP_OBJECT_ID" -Body $patchBody | Out-Null
Write-Host "    OK (redirect + roles)" -ForegroundColor Green

# 2) Ensure the app's service principal (needed to assign roles) --
Write-Host "2/4  Ensuring service principal..." -ForegroundColor Cyan
$spList = Invoke-Graph -Method GET -Path "/servicePrincipals?`$filter=appId eq '$APP_ID'&`$select=id"
if ($spList.value.Count -eq 0) {
    $sp = Invoke-Graph -Method POST -Path "/servicePrincipals" -Body @{ appId = $APP_ID }
    $SP_OBJECT_ID = $sp.id
    Write-Host "    created SP $SP_OBJECT_ID" -ForegroundColor Green
}
else {
    $SP_OBJECT_ID = $spList.value[0].id
    Write-Host "    SP already existed $SP_OBJECT_ID" -ForegroundColor Green
}

# 3) Resolve the user's objectId -----------------------------------------
Write-Host "3/4  Resolving user $USER_UPN..." -ForegroundColor Cyan
$user = Invoke-Graph -Method GET -Path "/users/$USER_UPN`?`$select=id,displayName"
$USER_ID = $user.id
Write-Host "    $($user.displayName) -> $USER_ID" -ForegroundColor Green

# 4) Assign BOTH roles to the user ----------------------------------------
Write-Host "4/4  Assigning roles to the user..." -ForegroundColor Cyan
$existing = Invoke-Graph -Method GET -Path "/users/$USER_ID/appRoleAssignments?`$select=id,appRoleId,resourceId"
foreach ($roleId in @($ROLE_CUSTOMER_ID, $ROLE_OPERATOR_ID)) {
    $already = $existing.value | Where-Object {
        $_.resourceId -eq $SP_OBJECT_ID -and $_.appRoleId -eq $roleId
    }
    if ($already) {
        Write-Host "    role $roleId  already assigned, skip" -ForegroundColor Yellow
        continue
    }
    Invoke-Graph -Method POST -Path "/users/$USER_ID/appRoleAssignments" -Body @{
        principalId = $USER_ID
        resourceId  = $SP_OBJECT_ID
        appRoleId   = $roleId
    } | Out-Null
    Write-Host "    role $roleId assigned" -ForegroundColor Green
}

Write-Host ""
Write-Host "Done. Configure the frontend with:" -ForegroundColor Cyan
Write-Host "    VITE_AUTH_ENABLED=true"
Write-Host "    VITE_AUTH_CLIENT_ID=$APP_ID"
Write-Host "    VITE_AUTH_TENANT_ID=$TENANT_ID"
Write-Host "And the backend with:"
Write-Host "    AUTH_ENABLED=true"
Write-Host "    AUTH_CLIENT_ID=$APP_ID"
Write-Host "    AUTH_TENANT_ID=$TENANT_ID"
