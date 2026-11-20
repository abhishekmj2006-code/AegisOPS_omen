@echo off
title Stop AegisOPS Platform
echo [..] Stopping all AegisOPS background processes...
powershell -Command "Get-Process python,pythonw -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*central-saas*' -or $_.CommandLine -like '*local-collector*' } | Stop-Process -Force"
echo [OK] AegisOPS processes stopped.
timeout /t 2 >nul
