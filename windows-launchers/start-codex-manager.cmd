@echo off
setlocal

for %%I in ("%~dp0.") do set "LAUNCHER_DIR=%%~fI"
set "WORKSPACE=%LAUNCHER_DIR%"
if not exist "%WORKSPACE%\HANDOFF.md" (
    for %%I in ("%LAUNCHER_DIR%\..") do set "WORKSPACE=%%~fI"
)
set "SCRIPT=%LAUNCHER_DIR%\start-codex-manager.ps1"
set "PID_FILE=%WORKSPACE%\.codex-manager\manage-cliproxy.pid"

if not exist "%SCRIPT%" (
    echo start-codex-manager.ps1 was not found at "%SCRIPT%"
    exit /b 1
)

if "%CLIPROXY_MANAGEMENT_KEY%"=="" (
    set /p CLIPROXY_MANAGEMENT_KEY=Enter CLIProxyAPI management key: 
)

if "%CLIPROXY_MANAGEMENT_KEY%"=="" (
    echo Management key is required.
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" -Workspace "%WORKSPACE%"
set "EXITCODE=%ERRORLEVEL%"
if not "%EXITCODE%"=="0" (
    exit /b %EXITCODE%
)

if exist "%PID_FILE%" (
    set /p PID=<"%PID_FILE%"
    if not "%PID%"=="" (
        echo codex-manager active with PID %PID%
    )
)

exit /b 0
