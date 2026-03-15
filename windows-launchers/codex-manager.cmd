@echo off
setlocal

for %%I in ("%~dp0.") do set "LAUNCHER_DIR=%%~fI"
set "WORKSPACE=%LAUNCHER_DIR%"
if not exist "%WORKSPACE%\HANDOFF.md" (
    for %%I in ("%LAUNCHER_DIR%\..") do set "WORKSPACE=%%~fI"
)

set "INSTALLED_SCRIPT=%USERPROFILE%\.codex\skills\codex-manager\scripts\codex_manager.py"
for %%I in ("%LAUNCHER_DIR%\..") do set "LOCAL_SKILL_ROOT=%%~fI"
set "LOCAL_SCRIPT=%LOCAL_SKILL_ROOT%\scripts\codex_manager.py"
set "SCRIPT=%INSTALLED_SCRIPT%"
if not exist "%SCRIPT%" (
    set "SCRIPT=%LOCAL_SCRIPT%"
)

if not exist "%SCRIPT%" (
    echo codex_manager.py was not found.
    exit /b 1
)

if "%~1"=="" (
    echo Usage: codex-manager.cmd ^<snapshot^|watch-cliproxy^|manage-cliproxy^|force-switch-cliproxy^|rotate-cliproxy^> [extra args]
    exit /b 1
)

set "COMMAND=%~1"
shift
set "EXTRA_ARGS="

:collect_args
if "%~1"=="" goto run_command
set "EXTRA_ARGS=%EXTRA_ARGS% "%~1""
shift
goto collect_args

:run_command
if /I "%COMMAND%"=="snapshot" (
    python "%SCRIPT%" snapshot --workspace "%WORKSPACE%" --project "%WORKSPACE%" --handoff "%WORKSPACE%\HANDOFF.md"%EXTRA_ARGS%
    exit /b %ERRORLEVEL%
)

if /I "%COMMAND%"=="watch-cliproxy" (
    python "%SCRIPT%" watch-cliproxy --workspace "%WORKSPACE%" --project "%WORKSPACE%" --handoff "%WORKSPACE%\HANDOFF.md"%EXTRA_ARGS%
    exit /b %ERRORLEVEL%
)

if /I "%COMMAND%"=="manage-cliproxy" (
    python "%SCRIPT%" manage-cliproxy --workspace "%WORKSPACE%" --project "%WORKSPACE%" --handoff "%WORKSPACE%\HANDOFF.md"%EXTRA_ARGS%
    exit /b %ERRORLEVEL%
)

if /I "%COMMAND%"=="force-switch-cliproxy" (
    python "%SCRIPT%" force-switch-cliproxy --workspace "%WORKSPACE%" --project "%WORKSPACE%" --handoff "%WORKSPACE%\HANDOFF.md"%EXTRA_ARGS%
    exit /b %ERRORLEVEL%
)

if /I "%COMMAND%"=="rotate-cliproxy" (
    python "%SCRIPT%" rotate-cliproxy --workspace "%WORKSPACE%" --project "%WORKSPACE%" --handoff "%WORKSPACE%\HANDOFF.md"%EXTRA_ARGS%
    exit /b %ERRORLEVEL%
)

python "%SCRIPT%" %COMMAND%%EXTRA_ARGS%
exit /b %ERRORLEVEL%
