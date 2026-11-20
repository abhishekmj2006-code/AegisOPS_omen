@echo off
echo =========================================================================
echo Starting AegisOPS Central SaaS Platform (Tier 2) on http://127.0.0.1:8000
echo - Web Dashboard:        http://127.0.0.1:8000/
echo - Privacy Audit Proof:  http://127.0.0.1:8000/privacy-audit
echo - OpenAPI Swagger Specs:http://127.0.0.1:8000/docs
echo =========================================================================
cd /d "%~dp0central-saas"
python main.py
pause
