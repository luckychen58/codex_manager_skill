param(
    [string]$Workspace,
    [string]$Project,
    [string]$Handoff,
    [string]$Provider = "codex",
    [string]$ManagerScript
)

$ErrorActionPreference = "Stop"

if (-not $Workspace) {
    $Workspace = $PSScriptRoot
    if (-not (Test-Path -LiteralPath (Join-Path $Workspace "HANDOFF.md"))) {
        $Workspace = Split-Path -Parent $Workspace
    }
}
if (-not $Project) {
    $Project = $Workspace
}
if (-not $Handoff) {
    $Handoff = Join-Path $Workspace "HANDOFF.md"
}
if (-not $ManagerScript) {
    $ManagerScript = Join-Path $PSScriptRoot "codex-manager.ps1"
}

if (-not (Test-Path -LiteralPath $ManagerScript)) {
    throw "codex-manager.ps1 was not found at $ManagerScript"
}

if (-not $env:CLIPROXY_MANAGEMENT_KEY) {
    $env:CLIPROXY_MANAGEMENT_KEY = Read-Host "Enter CLIProxyAPI management key"
}

if (-not $env:CLIPROXY_MANAGEMENT_KEY) {
    throw "Management key is required."
}

Write-Host "Rotating to the next healthy $Provider account..."

& powershell.exe `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File $ManagerScript `
    -Command "force-switch-cliproxy" `
    -Workspace $Workspace `
    -Project $Project `
    -Handoff $Handoff `
    -Provider $Provider

exit $LASTEXITCODE
