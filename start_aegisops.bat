@echo off
setlocal enabledelayedexpansion
title AegisOPS Unified Platform Launcher

echo =========================================================================
echo   [AegisOPS] Secure IT Monitoring & Autonomous Operations Platform
echo =========================================================================
echo.

set ROOT_DIR=%~dp0
set SAAS_PORT=8000
set TARGET_URL=https://aegisops-omen.onrender.com/

:: 1. Detect configured backend URL from local-collector\.env
if exist "%ROOT_DIR%local-collector\.env" (
    for /f "usebackq tokens=1,* delims==" %%A in ("%ROOT_DIR%local-collector\.env") do (
        if /i "%%A"=="BACKEND_URL" (
            set TARGET_URL=%%B
        )
    )
)

:: Sanitize URL
set TARGET_URL=%TARGET_URL:"=%
set TARGET_URL=%TARGET_URL: =%
if not "%TARGET_URL:~-1%"=="/" set TARGET_URL=%TARGET_URL%/

echo [..] Target Central SaaS URL: %TARGET_URL%

:: 2. If configured for local SaaS (127.0.0.1 or localhost), check and start local SaaS backend
echo %TARGET_URL% | findstr /i "127.0.0.1 localhost" >nul
if !ERRORLEVEL! equ 0 (
    echo [..] Local development mode detected. Checking local SaaS backend on port %SAAS_PORT%...
    powershell -Command "$c = Test-NetConnection -ComputerName 127.0.0.1 -Port %SAAS_PORT% -WarningAction SilentlyContinue; if ($c.TcpTestSucceeded) { exit 0 } else { exit 1 }"
    if !ERRORLEVEL! equ 0 (
        echo [OK] Central SaaS backend is already active on http://127.0.0.1:%SAAS_PORT%
    ) else (
        echo [..] Starting Central SaaS Backend in background on port %SAAS_PORT%...
        start "AegisOPS Central SaaS Backend" /min powershell -WindowStyle Minimized -Command "cd '%ROOT_DIR%central-saas'; python main.py"
        
        powershell -Command "for ($i=0; $i -lt 12; $i++) { try { $r = Invoke-RestMethod -Uri 'http://127.0.0.1:%SAAS_PORT%/api/v1/health' -TimeoutSec 1; if ($r.status -eq 'healthy') { exit 0 } } catch {}; Start-Sleep -Milliseconds 500 }; exit 1"
        if !ERRORLEVEL! equ 0 (
            echo [OK] Central SaaS backend is healthy and online!
        ) else (
            echo [WARN] Backend starting up, continuing...
        )
    )
) else (
    echo [OK] Live Cloud SaaS deployment detected: %TARGET_URL%
    echo      (Direct cloud streaming active; no local SaaS server needed)
)

:: 3. Open Central SaaS Dashboard in user's default web browser
echo.
echo [..] Opening Central SaaS Web Dashboard at %TARGET_URL% ...
start "" "%TARGET_URL%"

:: 4. Launch Local Collector GUI
echo.
echo [..] Launching AegisOPS Secure Local Collector Desktop GUI...
cd /d "%ROOT_DIR%local-collector"
python main.py

echo.
echo [AegisOPS] Local Collector GUI closed.
pause
