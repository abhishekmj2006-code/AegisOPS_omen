"""Web Dashboard routes serving enterprise browser interface."""

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timezone
import os
import json

from storage.database import get_db
from storage.repository import CentralRepository
from storage.models import TelemetryRecord
from saas_config.settings import settings
from saas_config.time_utils import to_local_datetime, format_local_12h, format_local_full, format_iso_utc_offset

router = APIRouter(include_in_schema=False)

templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)
templates.env.globals["format_local_12h"] = format_local_12h
templates.env.globals["format_local_full"] = format_local_full


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
    
    # Evaluate heartbeat staleness for fleet
    now = datetime.now(timezone.utc)
    for n in nodes:
        if n.last_heartbeat:
            hb = n.last_heartbeat if n.last_heartbeat.tzinfo else n.last_heartbeat.replace(tzinfo=timezone.utc)
            delta = (now - hb).total_seconds()
            if delta > settings.heartbeat_timeout_seconds:
                n.status = "offline"
                if n.health_state != "Poor":
                    n.health_state = "Poor"
                    n.health_reason = f"Collector offline: Heartbeat lost for {int(delta)}s (> {int(settings.heartbeat_timeout_seconds)}s)."
    db.commit()

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
    
    # Evaluate heartbeat staleness for fleet
    now = datetime.now(timezone.utc)
    for n in nodes:
        if n.last_heartbeat:
            hb = n.last_heartbeat if n.last_heartbeat.tzinfo else n.last_heartbeat.replace(tzinfo=timezone.utc)
            delta = (now - hb).total_seconds()
            if delta > settings.heartbeat_timeout_seconds:
                n.status = "offline"
                if n.health_state != "Poor":
                    n.health_state = "Poor"
                    n.health_reason = f"Collector offline: Heartbeat lost for {int(delta)}s (> {int(settings.heartbeat_timeout_seconds)}s)."
    db.commit()

    incidents = repo.get_incidents_by_tenant(tenant_id, limit=10)
    remediations = repo.get_remediations_by_tenant(tenant_id)
    sla = repo.get_sla_metrics(tenant_id)
    transitions = repo.get_health_transitions(tenant_id, limit=10)
    audit_trail = repo.get_all_remediation_audit_entries(tenant_id, limit=12)

    # Health distribution
    health_counts = {"Excellent": 0, "Good": 0, "Fair": 0, "Poor": 0}
    for n in nodes:
        if n.health_state in health_counts:
            health_counts[n.health_state] += 1

    return {
        "tenant_id": tenant_id,
        "health_counts": health_counts,
        "nodes": [
            {
                "device_id": n.device_id,
                "hostname": n.hostname or "unknown-host",
                "os_info": n.os_info or "Unknown OS",
                "version": n.version or "2.0.0",
                "architecture": n.architecture or "x86_64",
                "region": n.region or "ap-south-1",
                "health_state": n.health_state,
                "health_reason": n.health_reason,
                "status": n.status,
                "collector_cpu_overhead": getattr(n, "collector_cpu_overhead", 0.2),
                "collector_ram_overhead": getattr(n, "collector_ram_overhead", 24.5),
                "config_status": getattr(n, "config_status", "synced"),
                "last_heartbeat": format_iso_utc_offset(n.last_heartbeat),
                "formatted_heartbeat": format_local_12h(n.last_heartbeat),
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
                "created_at": format_local_12h(inc.created_at),
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
                "timestamp": format_local_12h(t.timestamp),
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
    nodes = repo.get_fleet_by_tenant(tenant_id)
    node_map = {n.device_id: n for n in nodes}

    # Fetch latest 50 records in arrival (received_at) order
    records_desc = (
        repo.session.query(TelemetryRecord)
        .filter(TelemetryRecord.tenant_id == tenant_id)
        .order_by(desc(TelemetryRecord.received_at))
        .limit(50)
        .all()
    )
    total_count = repo.session.query(TelemetryRecord).filter(TelemetryRecord.tenant_id == tenant_id).count()

    return templates.TemplateResponse(
        request=request,
        name="audit.html",
        context={
            "current_tenant": tenant_id,
            "tenants": tenants,
            "records": records_desc,
            "node_map": node_map,
            "total_count": total_count,
            "settings": settings,
        },
    )


@router.get("/api/v1/dashboard/privacy-audit/records")
def privacy_audit_records_api(
    tenant_id: str = Query("TENANT_001"),
    limit: int = Query(50, ge=5, le=100),
    db: Session = Depends(get_db),
):
    """Real-time JSON endpoint for privacy audit dynamic live streaming."""
    repo = CentralRepository(db)
    nodes = repo.get_fleet_by_tenant(tenant_id)
    node_map = {n.device_id: n for n in nodes}

    total_count = repo.session.query(TelemetryRecord).filter(TelemetryRecord.tenant_id == tenant_id).count()
    records_desc = (
        repo.session.query(TelemetryRecord)
        .filter(TelemetryRecord.tenant_id == tenant_id)
        .order_by(desc(TelemetryRecord.received_at))
        .limit(limit)
        .all()
    )

    serialized = []
    for r in records_desc:
        node = node_map.get(r.device_id)
        raw_m = {}
        if r.raw_metrics_json:
            try:
                raw_m = json.loads(r.raw_metrics_json)
            except Exception:
                raw_m = {}
        serialized.append({
            "message_id": r.message_id,
            "tenant_id": r.tenant_id,
            "device_id": r.device_id,
            "hostname": (node.hostname if node and node.hostname else r.device_id),
            "os_info": (node.os_info if node and node.os_info else "Unknown OS"),
            "architecture": (node.architecture if node and node.architecture else "x86_64"),
            "collector_version": (getattr(node, "collector_version", "2.0.0") if node else "2.0.0"),
            "region": r.region,
            "source_timezone": r.source_timezone or "India Standard Time",
            "metrics": raw_m,
            "collector_status": r.collector_status,
            "is_anomaly": bool(r.is_anomaly),
            "formatted_event_time": format_local_full(r.event_time),
            "raw_event_time": format_iso_utc_offset(r.event_time),
        })

    return {
        "tenant_id": tenant_id,
        "total_count": total_count,
        "count": len(serialized),
        "records": serialized,
    }
