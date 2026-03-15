param(
    [ValidateSet("snapshot", "watch-cliproxy", "manage-cliproxy", "force-switch-cliproxy", "rotate-cliproxy")]
    [string]$Command = "snapshot",
    [string]$Workspace,
    [string]$Project,
    [string]$Handoff,
    [string]$ProjectName,
    [string]$Objective,
    [string]$Artifact,
    [string[]]$KeyFile,
    [string[]]$NextStep,
    [string[]]$Risk,
    [string[]]$StatusLine,
    [int]$MaxRecentFiles = 8,
    [int]$MaxGitLines = 20,
    [switch]$DryRun,
    [string]$BaseUrl = "http://127.0.0.1:8317",
    [string]$ManagementKey,
    [string]$ManagementKeyEnv = "CLIPROXY_MANAGEMENT_KEY",
    [string[]]$Provider,
    [int]$PollSeconds = 20,
    [int]$CooldownSeconds = 300,
    [switch]$Once
)

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "python was not found in PATH"
}

$installedRoot = Join-Path $HOME ".codex\skills\codex-manager"
$localRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $installedRoot "scripts\codex_manager.py"
if (-not (Test-Path -LiteralPath $scriptPath)) {
    $scriptPath = Join-Path $localRoot "scripts\codex_manager.py"
}
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "codex_manager.py was not found in the installed skill or local clone"
}

if (-not $Workspace) {
    $Workspace = $PSScriptRoot
    if (-not (Test-Path -LiteralPath (Join-Path $Workspace "HANDOFF.md"))) {
        $Workspace = Split-Path -Parent $Workspace
    }
}

$resolvedWorkspace = (Resolve-Path -LiteralPath $Workspace).Path
if (-not $Project) {
    $Project = $resolvedWorkspace
}
$resolvedProject = (Resolve-Path -LiteralPath $Project).Path
if (-not $Handoff) {
    $Handoff = Join-Path $resolvedWorkspace "HANDOFF.md"
}

$arguments = @(
    $scriptPath,
    $Command,
    "--workspace", $resolvedWorkspace,
    "--project", $resolvedProject,
    "--handoff", $Handoff,
    "--max-recent-files", "$MaxRecentFiles",
    "--max-git-lines", "$MaxGitLines"
)

if ($ProjectName) {
    $arguments += @("--project-name", $ProjectName)
}
if ($Objective) {
    $arguments += @("--objective", $Objective)
}
if ($Artifact) {
    $arguments += @("--artifact", $Artifact)
}
foreach ($item in $KeyFile) {
    if ($item) {
        $arguments += @("--key-file", $item)
    }
}
foreach ($item in $NextStep) {
    if ($item) {
        $arguments += @("--next-step", $item)
    }
}
foreach ($item in $Risk) {
    if ($item) {
        $arguments += @("--risk", $item)
    }
}
foreach ($item in $StatusLine) {
    if ($item) {
        $arguments += @("--status-line", $item)
    }
}
if ($DryRun) {
    $arguments += "--dry-run"
}

if ($Command -eq "watch-cliproxy") {
    $arguments += @("--base-url", $BaseUrl)
    $arguments += @("--management-key-env", $ManagementKeyEnv)
    if ($ManagementKey) {
        $arguments += @("--management-key", $ManagementKey)
    }
    foreach ($item in $Provider) {
        if ($item) {
            $arguments += @("--provider", $item)
        }
    }
    $arguments += @("--poll-seconds", "$PollSeconds")
    $arguments += @("--cooldown-seconds", "$CooldownSeconds")
    if ($Once) {
        $arguments += "--once"
    }
}

if ($Command -in @("manage-cliproxy", "force-switch-cliproxy", "rotate-cliproxy")) {
    $arguments += @("--base-url", $BaseUrl)
    $arguments += @("--management-key-env", $ManagementKeyEnv)
    if ($ManagementKey) {
        $arguments += @("--management-key", $ManagementKey)
    }
    foreach ($item in $Provider) {
        if ($item) {
            $arguments += @("--provider-name", $item)
        }
    }
    if ($Command -eq "manage-cliproxy") {
        $arguments += @("--poll-seconds", "$PollSeconds")
    }
    if ($Once -and $Command -eq "manage-cliproxy") {
        $arguments += "--once"
    }
}

& $python.Source @arguments
exit $LASTEXITCODE
