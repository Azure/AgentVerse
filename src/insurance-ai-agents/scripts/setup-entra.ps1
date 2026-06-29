# Configura el app registration `insurance-ai-demo-spa` para la demo:
# - Añade SPA platform con redirect URIs (localhost:5173 + Static Web App)
# - Define los 2 App Roles (Customer.Submit, Operator.Review)
# - Asigna AMBOS roles al usuario indicado (para que pueda alternar en la demo)
#
# REQUISITOS:
#   az login --tenant <TU_TENANT> --scope https://graph.microsoft.com//.default
#   $TENANT_ID, $APP_OBJECT_ID y $USER_UPN ya están seteados abajo.
#
# Si tu tenant tiene CAE activo y devuelve TokenCreatedWithOutdatedPolicies:
#   az logout
#   az login --tenant 763b21d6-9a2e-4d90-88f9-d3c5cc8dba90

$ErrorActionPreference = 'Stop'

$AZ            = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
$TENANT_ID     = "763b21d6-9a2e-4d90-88f9-d3c5cc8dba90"
$APP_OBJECT_ID = "d3fd01da-0941-4bfc-b3c4-f8a63a19de91"
$APP_ID        = "4e593597-088c-404c-984c-203259ff7dbe"
$USER_UPN      = "admin@MngEnvMCAP135050.onmicrosoft.com"
$REDIRECT_URIS = @(
    "http://localhost:5173",
    "http://localhost:5173/"
)

# IDs estables (mismo que app-roles.json) ----------------------------------
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
Write-Host "1/4  Configurando SPA redirect URIs y App Roles..." -ForegroundColor Cyan
$patchBody = @{
    spa = @{ redirectUris = $REDIRECT_URIS }
    appRoles = @(
        @{
            id                 = $ROLE_CUSTOMER_ID
            allowedMemberTypes = @("User")
            description        = "Puede crear y consultar sus propios siniestros."
            displayName        = "Customer (cliente)"
            isEnabled          = $true
            value              = "Customer.Submit"
        },
        @{
            id                 = $ROLE_OPERATOR_ID
            allowedMemberTypes = @("User")
            description        = "Puede ver todos los siniestros, cola de revision humana, estadisticas y panel de seguridad/gobernanza."
            displayName        = "Operator (operario)"
            isEnabled          = $true
            value              = "Operator.Review"
        }
    )
}
Invoke-Graph -Method PATCH -Path "/applications/$APP_OBJECT_ID" -Body $patchBody | Out-Null
Write-Host "    OK (redirect + roles)" -ForegroundColor Green

# 2) Garantizar service principal del app (necesario para asignar roles) --
Write-Host "2/4  Asegurando service principal..." -ForegroundColor Cyan
$spList = Invoke-Graph -Method GET -Path "/servicePrincipals?`$filter=appId eq '$APP_ID'&`$select=id"
if ($spList.value.Count -eq 0) {
    $sp = Invoke-Graph -Method POST -Path "/servicePrincipals" -Body @{ appId = $APP_ID }
    $SP_OBJECT_ID = $sp.id
    Write-Host "    creado SP $SP_OBJECT_ID" -ForegroundColor Green
} else {
    $SP_OBJECT_ID = $spList.value[0].id
    Write-Host "    ya existia SP $SP_OBJECT_ID" -ForegroundColor Green
}

# 3) Resolver objectId del usuario -----------------------------------------
Write-Host "3/4  Resolviendo usuario $USER_UPN..." -ForegroundColor Cyan
$user = Invoke-Graph -Method GET -Path "/users/$USER_UPN`?`$select=id,displayName"
$USER_ID = $user.id
Write-Host "    $($user.displayName) -> $USER_ID" -ForegroundColor Green

# 4) Asignar AMBOS roles al usuario ----------------------------------------
Write-Host "4/4  Asignando roles al usuario..." -ForegroundColor Cyan
$existing = Invoke-Graph -Method GET -Path "/users/$USER_ID/appRoleAssignments?`$select=id,appRoleId,resourceId"
foreach ($roleId in @($ROLE_CUSTOMER_ID, $ROLE_OPERATOR_ID)) {
    $already = $existing.value | Where-Object {
        $_.resourceId -eq $SP_OBJECT_ID -and $_.appRoleId -eq $roleId
    }
    if ($already) {
        Write-Host "    role $roleId  ya asignado, skip" -ForegroundColor Yellow
        continue
    }
    Invoke-Graph -Method POST -Path "/users/$USER_ID/appRoleAssignments" -Body @{
        principalId = $USER_ID
        resourceId  = $SP_OBJECT_ID
        appRoleId   = $roleId
    } | Out-Null
    Write-Host "    role $roleId asignado" -ForegroundColor Green
}

Write-Host ""
Write-Host "Listo. Configura el frontend con:" -ForegroundColor Cyan
Write-Host "    VITE_AUTH_ENABLED=true"
Write-Host "    VITE_AUTH_CLIENT_ID=$APP_ID"
Write-Host "    VITE_AUTH_TENANT_ID=$TENANT_ID"
Write-Host "Y el backend con:"
Write-Host "    AUTH_ENABLED=true"
Write-Host "    AUTH_CLIENT_ID=$APP_ID"
Write-Host "    AUTH_TENANT_ID=$TENANT_ID"
