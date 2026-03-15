param(
    [string]$Workspace,
    [string]$Project,
    [string]$Handoff,
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

$stateDir = Join-Path $Workspace ".codex-manager"
$outLog = Join-Path $stateDir "manage-cliproxy.stdout.log"
$errLog = Join-Path $stateDir "manage-cliproxy.stderr.log"
$pidFile = Join-Path $stateDir "manage-cliproxy.pid"

if (-not (Test-Path -LiteralPath $ManagerScript)) {
    throw "codex-manager.ps1 was not found at $ManagerScript"
}

if (-not $env:CLIPROXY_MANAGEMENT_KEY) {
    throw "Management key is required. Set CLIPROXY_MANAGEMENT_KEY before starting."
}

if (-not (Test-Path -LiteralPath $stateDir)) {
    New-Item -ItemType Directory -Path $stateDir | Out-Null
}

if (Test-Path -LiteralPath $pidFile) {
    $existingPid = [string](Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue -TotalCount 1)
    $existingPid = $existingPid.Trim()
    if ($existingPid -match '^[0-9]+$') {
        $existing = Get-Process -Id ([int]$existingPid) -ErrorAction SilentlyContinue
        if ($existing) {
            Write-Host "codex-manager is already running with PID $existingPid"
            Write-Host "Stdout log: `"$outLog`""
            Write-Host "Stderr log: `"$errLog`""
            exit 0
        }
    }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

$proc = Start-Process `
    -FilePath "powershell.exe" `
    -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $ManagerScript,
        "-Command", "manage-cliproxy",
        "-Workspace", $Workspace,
        "-Project", $Project,
        "-Handoff", $Handoff
    ) `
    -WorkingDirectory $Workspace `
    -RedirectStandardOutput $outLog `
    -RedirectStandardError $errLog `
    -WindowStyle Hidden `
    -PassThru

Set-Content -LiteralPath $pidFile -Value $proc.Id -NoNewline

Write-Host "Started codex-manager with PID $($proc.Id)"
Write-Host "Stdout log: `"$outLog`""
Write-Host "Stderr log: `"$errLog`""
