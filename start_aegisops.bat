@echo off
setlocal enabledelayedexpansion
title AegisOPS Unified Platform Launcher

echo =========================================================================
echo   [AegisOPS] Secure IT Monitoring & Autonomous Operations Platform
echo =========================================================================
echo.

set SAAS_PORT=8000
set ROOT_DIR=%~dp0

:: 1. Check if Central SaaS backend is already online on port 8000
powershell -Command "$c = Test-NetConnection -ComputerName 127.0.0.1 -Port %SAAS_PORT% -WarningAction SilentlyContinue; if ($c.TcpTestSucceeded) { exit 0 } else { exit 1 }"
if %ERRORLEVEL% equ 0 (
    echo [OK] Central SaaS backend is already active on http://127.0.0.1:%SAAS_PORT%
) else (
    echo [..] Starting Central SaaS Backend in background on port %SAAS_PORT%...
    start "AegisOPS Central SaaS Backend" /min powershell -WindowStyle Minimized -Command "cd '%ROOT_DIR%central-saas'; python main.py"
    
    :: Wait up to 6 seconds for backend to become healthy
    echo [..] Waiting for SaaS backend to initialize...
    powershell -Command "for ($i=0; $i -lt 12; $i++) { try { $r = Invoke-RestMethod -Uri 'http://127.0.0.1:%SAAS_PORT%/api/v1/health' -TimeoutSec 1; if ($r.status -eq 'healthy') { exit 0 } } catch {}; Start-Sleep -Milliseconds 500 }; exit 1"
    if %ERRORLEVEL% equ 0 (
        echo [OK] Central SaaS backend is healthy and online!
    ) else (
        echo [WARN] Backend starting up, continuing...
    )
)

:: 2. Open Central SaaS Dashboard in user's default web browser
echo [..] Opening Central SaaS Web Dashboard in your browser...
start http://127.0.0.1:%SAAS_PORT%/

:: 3. Launch Local Collector GUI
echo [..] Launching AegisOPS Secure Local Collector Desktop GUI...
cd /d "%ROOT_DIR%local-collector"
python main.py

echo.
echo [AegisOPS] Local Collector GUI closed.
pause
