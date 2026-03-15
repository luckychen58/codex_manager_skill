@echo off
setlocal

for %%I in ("%~dp0.") do set "LAUNCHER_DIR=%%~fI"
set "WORKSPACE=%LAUNCHER_DIR%"
if not exist "%WORKSPACE%\.codex-manager\manage-cliproxy.pid" (
    for %%I in ("%LAUNCHER_DIR%\..") do set "WORKSPACE=%%~fI"
)
set "PID_FILE=%WORKSPACE%\.codex-manager\manage-cliproxy.pid"

if not exist "%PID_FILE%" (
    echo PID file not found: "%PID_FILE%"
    exit /b 1
)

set /p PID=<"%PID_FILE%"
if "%PID%"=="" (
    echo PID file is empty.
    exit /b 1
)

taskkill /PID %PID% /T /F
if errorlevel 1 (
    echo Failed to stop process %PID%.
    exit /b 1
)

del "%PID_FILE%" >nul 2>nul
echo Stopped codex-manager process %PID%.
