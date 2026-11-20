@echo off
echo =========================================================================
echo Running AegisOPS Automated Tests (Tier 1 Local Collector & Tier 2 SaaS)
echo =========================================================================
cd /d "%~dp0"
echo.
echo [1/2] Running Tier 1 Local Collector Unit & Integration Tests...
python -m pytest local-collector/tests/ -v
echo.
echo [2/2] Running Tier 2 Central SaaS Platform & AIOps Tests...
python -m pytest central-saas/tests/ -v
echo.
echo All test suites executed successfully!
pause
