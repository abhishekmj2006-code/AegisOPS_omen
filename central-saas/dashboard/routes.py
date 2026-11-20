"""Web Dashboard routes serving enterprise browser interface."""

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os

from storage.database import get_db
from storage.repository import CentralRepository
from saas_config.settings import settings

router = APIRouter(include_in_schema=False)

templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)


@router.get("/", response_class=HTMLResponse)
def dashboard_view(
    request: Request,
    tenant_id: str = Query("TENANT_001"),
    db: Session = Depends(get_db),
):
    """Primary central SaaS operational dashboard."""
    repo = CentralRepository(db)
    tenants = repo.get_all_tenants()
    nodes = repo.get_fleet_by_tenant(tenant_id)
    incidents = repo.get_incidents_by_tenant(tenant_id, limit=10)
    remediations = repo.get_remediations_by_tenant(tenant_id)
    recent_telemetry = repo.get_telemetry_series(tenant_id, limit=20)
    sla = repo.get_sla_metrics(tenant_id)
    transitions = repo.get_health_transitions(tenant_id, limit=10)
    audit_trail = repo.get_all_remediation_audit_entries(tenant_id, limit=12)

    # Health distribution
    health_counts = {"Excellent": 0, "Good": 0, "Fair": 0, "Poor": 0}
    for n in nodes:
        if n.health_state in health_counts:
            health_counts[n.health_state] += 1

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "current_tenant": tenant_id,
            "tenants": tenants,
            "nodes": nodes,
            "incidents": incidents,
            "remediations": remediations,
            "recent_telemetry": recent_telemetry,
            "health_counts": health_counts,
            "sla": sla,
            "transitions": transitions,
            "audit_trail": audit_trail,
            "settings": settings,
        },
    )


@router.get("/api/v1/dashboard/live-state")
def live_dashboard_state(
    tenant_id: str = Query("TENANT_001"),
    db: Session = Depends(get_db),
):
    """Real-time JSON state endpoint for non-disruptive dashboard DOM polling."""
    repo = CentralRepository(db)
    nodes = repo.get_fleet_by_tenant(tenant_id)
    incidents = repo.get_incidents_by_tenant(tenant_id, limit=10)
    remediations = repo.get_remediations_by_tenant(tenant_id)
    sla = repo.get_sla_metrics(tenant_id)
    transitions = repo.get_health_transitions(tenant_id, limit=10)
    audit_trail = repo.get_all_remediation_audit_entries(tenant_id, limit=12)

    return {
        "tenant_id": tenant_id,
        "nodes": [
            {
                "device_id": n.device_id,
                "hostname": n.hostname,
                "os_info": n.os_info,
                "version": n.version,
                "architecture": n.architecture,
                "region": n.region,
                "health_state": n.health_state,
                "health_reason": n.health_reason,
                "status": n.status,
                "collector_cpu_overhead": getattr(n, "collector_cpu_overhead", 0.2),
                "collector_ram_overhead": getattr(n, "collector_ram_overhead", 24.5),
                "config_status": getattr(n, "config_status", "synced"),
            }
            for n in nodes
        ],
        "incidents": [
            {
                "id": inc.id,
                "title": inc.title,
                "category": inc.category,
                "severity": inc.severity,
                "status": inc.status,
                "root_cause": inc.root_cause,
                "explanation": inc.explanation,
                "confidence_score": inc.confidence_score,
                "ai_engine": getattr(inc, "ai_engine", "Deterministic AIOps Engine"),
                "occurrence_count": getattr(inc, "occurrence_count", 1),
                "created_at": inc.created_at.strftime("%I:%M:%S %p") if inc.created_at else "",
                "remediations": [
                    {
                        "id": r.id,
                        "title": r.title,
                        "description": r.description,
                        "status": r.status,
                        "policy_check": r.policy_check,
                    }
                    for r in inc.remediations
                ],
            }
            for inc in incidents
        ],
        "sla": sla,
        "transitions": [
            {
                "device_id": t.device_id,
                "previous_state": t.previous_state,
                "new_state": t.new_state,
                "reason": t.reason,
                "timestamp": t.timestamp.strftime("%I:%M:%S %p") if t.timestamp else "",
            }
            for t in transitions
        ],
        "audit_trail": audit_trail,
    }


@router.get("/privacy-audit", response_class=HTMLResponse)
def privacy_audit_view(
    request: Request,
    tenant_id: str = Query("TENANT_001"),
    db: Session = Depends(get_db),
):
    """Side-by-side privacy verification panel proving metadata-only ingest and tenant separation."""
    repo = CentralRepository(db)
    tenants = repo.get_all_tenants()
    records = repo.get_telemetry_series(tenant_id, limit=15)

    return templates.TemplateResponse(
        request=request,
        name="audit.html",
        context={
            "current_tenant": tenant_id,
            "tenants": tenants,
            "records": records,
            "settings": settings,
        },
    )
