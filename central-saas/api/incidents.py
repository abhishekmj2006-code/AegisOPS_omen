"""Incidents & Telemetry Queries API."""

import json
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from storage.database import get_db
from storage.repository import CentralRepository
from storage.models import Incident

router = APIRouter(prefix="/api/v1/incidents", tags=["Incidents & Telemetry"])


@router.get("")
def list_incidents(
    tenant_id: str = Query("TENANT_001", description="Tenant isolation scope"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Retrieve correlated multi-signal incidents for tenant."""
    repo = CentralRepository(db)
    incidents = repo.get_incidents_by_tenant(tenant_id, limit=limit)

    return {
        "tenant_id": tenant_id,
        "total_incidents": len(incidents),
        "incidents": [
            {
                "id": inc.id,
                "device_id": inc.device_id,
                "title": inc.title,
                "category": inc.category,
                "severity": inc.severity,
                "status": inc.status,
                "root_cause": inc.root_cause,
                "explanation": inc.explanation,
                "confidence_score": inc.confidence_score,
                "ai_engine": getattr(inc, "ai_engine", "Deterministic AIOps Engine"),
                "contributing_signals": inc.get_contributing_signals(),
                "created_at": inc.created_at.isoformat() if inc.created_at else None,
            }
            for inc in incidents
        ],
    }


@router.get("/telemetry")
def get_telemetry_series(
    tenant_id: str = Query("TENANT_001", description="Tenant isolation boundary"),
    device_id: Optional[str] = Query(None),
    limit: int = Query(60, ge=5, le=300),
    minutes: Optional[int] = Query(None, description="Time range in minutes (5, 15, 60)"),
    db: Session = Depends(get_db),
):
    """Retrieve time-series telemetry ordered by EVENT TIME (out-of-order resilient)."""
    repo = CentralRepository(db)
    min_val = minutes if isinstance(minutes, int) else None
    records = repo.get_telemetry_series(tenant_id, device_id=device_id, limit=limit, minutes=min_val)

    return {
        "tenant_id": tenant_id,
        "count": len(records),
        "series": [
            {
                "message_id": r.message_id,
                "device_id": r.device_id,
                "event_time": r.event_time.isoformat() if r.event_time else None,
                "received_at": r.received_at.isoformat() if r.received_at else None,
                "cpu_usage": r.cpu_usage,
                "ram_usage": r.ram_usage,
                "disk_usage": r.disk_usage,
                "network_latency_ms": r.network_latency_ms,
                "packet_loss_percent": r.packet_loss_percent,
                "failed_login_count": r.failed_login_count,
                "is_anomaly": r.is_anomaly,
                "anomaly_signals": json.loads(r.anomaly_signals or "[]"),
            }
            for r in records
        ],
    }
