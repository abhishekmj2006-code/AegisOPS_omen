"""AegisOPS Central SaaS Platform — Main Application Entry Point.

Runs the multi-tenant AIOps observability platform on port 8000.
Provides:
- Ingestion API with UUID idempotency and regional validation
- Live fleet management with four-state health classification
- Dynamic AIOps anomaly detection, alert correlation, and explainable recommendations
- Autonomous Ops safe remediation with human-in-the-loop approvals and rollback
- Executive web dashboard with real-time Chart.js telemetry curves and privacy proof
"""

import sys
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Ensure package roots are on sys.path
sys.path.insert(0, os.path.dirname(__file__))

from saas_config.settings import settings
from storage.database import init_db
from api.ingest import router as ingest_router
from api.fleet import router as fleet_router
from api.incidents import router as incidents_router
from api.remediation import router as remediation_router
from api.scenarios import router as scenarios_router
from dashboard.routes import router as dashboard_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and seed default tenants upon startup."""
    init_db()
    print("=" * 75)
    print("  🛡️  AegisOPS Central SaaS Platform (Tier 2)")
    print(f"  • Server URL: http://127.0.0.1:{settings.port}")
    print(f"  • Web Dashboard: http://127.0.0.1:{settings.port}/")
    print(f"  • Privacy Audit Proof: http://127.0.0.1:{settings.port}/privacy-audit")
    print(f"  • OpenAPI Swagger Docs: http://127.0.0.1:{settings.port}/docs")
    print(f"  • Default Tenants: TENANT_001 (Production), TENANT_002 (DR)")
    print("=" * 75)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Tier 2 Central SaaS Platform providing metadata-only ingestion, AIOps correlation, four-state health evaluation, and safe autonomous ops.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API & Dashboard Routers
app.include_router(ingest_router)
app.include_router(fleet_router)
app.include_router(incidents_router)
app.include_router(remediation_router)
app.include_router(scenarios_router)
app.include_router(dashboard_router)


if __name__ == "__main__":
    ssl_certfile = os.getenv("SSL_CERTFILE")
    ssl_keyfile = os.getenv("SSL_KEYFILE")
    run_kwargs = {
        "app": "main:app",
        "host": settings.host,
        "port": settings.port,
        "reload": False,
    }
    if ssl_certfile and ssl_keyfile and os.path.exists(ssl_certfile) and os.path.exists(ssl_keyfile):
        run_kwargs["ssl_certfile"] = ssl_certfile
        run_kwargs["ssl_keyfile"] = ssl_keyfile
        print(f"🔒 TLS/HTTPS Enabled with certificate: {ssl_certfile}")
    uvicorn.run(**run_kwargs)
