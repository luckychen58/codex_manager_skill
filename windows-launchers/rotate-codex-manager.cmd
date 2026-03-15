@echo off
setlocal

set "SCRIPT=%~dp0rotate-codex-manager.ps1"

if not exist "%SCRIPT%" (
    echo rotate-codex-manager.ps1 was not found at "%SCRIPT%"
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%"
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
    echo Rotate finished.
) else (
    echo Rotate failed with exit code %EXITCODE%.
)

pause
exit /b %EXITCODE%
