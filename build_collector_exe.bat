@echo off
title Build AegisOPS Standalone Executable (.exe)
echo =========================================================================
echo   Building AegisOPS Local Collector Standalone Desktop Executable
echo =========================================================================
echo.

pip install pyinstaller
if %ERRORLEVEL% neq 0 (
    echo Failed to install PyInstaller.
    pause
    exit /b 1
)

cd /d "%~dp0local-collector"
pyinstaller --noconfirm --onedir --windowed --name "AegisOPS-Collector" --add-data "interface;interface" --add-data "config;config" main.py

echo.
echo =========================================================================
echo   Build complete! Output located at: local-collector\dist\AegisOPS-Collector
echo =========================================================================
pause
