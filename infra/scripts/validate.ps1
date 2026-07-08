# ============================================================================
# Local validation for the AgentVerse global deploy. Runs everything that can
# be checked WITHOUT an Azure subscription:
#   1. Validate every demo's agentverse.yaml + regenerate the catalog.
#   2. Copy the catalog into the portal image build context.
#   3. terraform fmt + validate.
#   4. Catalog <-> Terraform topology consistency check.
# The real deployment (terraform apply) is run separately by the operator.
# ============================================================================
param(
    [switch]$SkipTerraform
)

$ErrorActionPreference = "Stop"
$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Write-Host "AgentVerse local validation (repo: $repo)" -ForegroundColor Cyan

# 1. Catalog -----------------------------------------------------------------
Write-Host "`n[1/4] Validating manifests + building catalog..." -ForegroundColor Yellow
python "$repo/src/templates/catalog/build_catalog.py" --check
python "$repo/src/templates/catalog/build_catalog.py" --write

# 2. Bake catalog into the portal build context ------------------------------
Write-Host "`n[2/4] Copying catalog.json into the portal..." -ForegroundColor Yellow
Copy-Item "$repo/src/catalog.json" "$repo/portal/public/catalog.json" -Force
Write-Host "  portal/public/catalog.json updated."

# 3. Terraform ---------------------------------------------------------------
if (-not $SkipTerraform) {
    Write-Host "`n[3/4] terraform fmt + validate..." -ForegroundColor Yellow
    Push-Location "$repo/infra"
    terraform fmt -recursive -check
    terraform init -backend=false -input=false | Out-Null
    terraform validate
    Pop-Location
} else {
    Write-Host "`n[3/4] Skipping Terraform (-SkipTerraform)." -ForegroundColor DarkGray
}

# 4. Consistency -------------------------------------------------------------
Write-Host "`n[4/4] Catalog <-> topology consistency..." -ForegroundColor Yellow
python "$repo/infra/scripts/check-consistency.py"

Write-Host "`nLocal validation complete." -ForegroundColor Green
