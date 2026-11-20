"""Metadata Ingest Endpoints with Strict Idempotency, Regional Routing, and AIOps Hook."""

from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Response, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from storage.database import get_db
from storage.repository import CentralRepository
from aiops.health_classifier import HealthClassifier
from aiops.anomaly_detector import AnomalyDetector
from aiops.correlator import EventCorrelator
from aiops.recommender import ExplainableRecommender
from saas_config.settings import settings

router = APIRouter(prefix="/api/v1", tags=["Ingestion"])


class HeartbeatPayload(BaseModel):
    device_id: str
    tenant_id: Optional[str] = "TENANT_001"
    timestamp: Optional[str] = None
    collector_status: Optional[str] = "online"
    hostname: Optional[str] = None
    os_info: Optional[str] = None
    architecture: Optional[str] = None
    version: Optional[str] = None
    region: Optional[str] = None
    collector_cpu_overhead: Optional[float] = None
    collector_ram_overhead: Optional[float] = None
    config_status: Optional[str] = None


def verify_collector_token(authorization: Optional[str]) -> None:
    """Enforces Bearer token collector authentication."""
    if not settings.require_collector_auth:
        return
    if not isinstance(authorization, str) or not authorization.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header. Expected: Bearer <collector_token>",
        )
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected: Bearer <collector_token>",
        )
    token = parts[1].strip()
    if token not in settings.valid_collector_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or unauthorized collector token.",
        )


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint for local collector connectivity verification."""
    repo = CentralRepository(db)
    tenants = repo.get_all_tenants()
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_tenants": [t.id for t in tenants],
        "regions_supported": settings.allowed_regions,
    }


@router.post("/heartbeat")
def receive_heartbeat(
    payload: HeartbeatPayload,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
    db: Session = Depends(get_db),
):
    """Collector presence heartbeat. Updates last-seen timestamp and maintains online state."""
    verify_collector_token(authorization)
    t_hdr = x_tenant_id if isinstance(x_tenant_id, str) else None
    d_hdr = x_device_id if isinstance(x_device_id, str) else None
    tenant_id = t_hdr or payload.tenant_id or "TENANT_001"
    device_id = d_hdr or payload.device_id

    repo = CentralRepository(db)
    collector = repo.upsert_collector(
        tenant_id=tenant_id,
        device_id=device_id,
        hostname=payload.hostname or "unknown-host",
        os_info=payload.os_info or "Unknown OS",
        architecture=payload.architecture or "x86_64",
        version=payload.version or "2.0.0",
        region=payload.region or settings.default_region,
        collector_cpu_overhead=payload.collector_cpu_overhead,
        collector_ram_overhead=payload.collector_ram_overhead,
        config_status=payload.config_status or "synced",
    )
    
    # Re-evaluate health state
    state, reason = HealthClassifier.evaluate_node(collector, latest_metrics={})
    repo.update_collector_health(tenant_id, device_id, state, reason, status="online")
    db.commit()

    return {
        "status": "alive",
        "device_id": device_id,
        "tenant_id": tenant_id,
        "health_state": state,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/metrics")
def receive_metrics(
    payload: Dict[str, Any],
    response: Response,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
    x_source_timezone: Optional[str] = Header(None, alias="X-Source-Timezone"),
    db: Session = Depends(get_db),
):
    """Ingest allow-listed metadata with strict UUID idempotency.
    
    If message_id was previously received: returns 200 OK (duplicate rejected safely).
    If new: ingests, triggers AIOps pipeline, returns 201 Created.
    """
    verify_collector_token(authorization)
    message_id = payload.get("message_id")
    if not message_id:
        raise HTTPException(status_code=400, detail="Missing mandatory 'message_id' (UUID required for idempotency)")

    t_hdr = x_tenant_id if isinstance(x_tenant_id, str) else None
    d_hdr = x_device_id if isinstance(x_device_id, str) else None
    tz_hdr = x_source_timezone if isinstance(x_source_timezone, str) else None

    tenant_id = payload.get("tenant_id") or t_hdr or "TENANT_001"
    device_id = payload.get("device_id") or d_hdr or "DEVICE_001"
    region = payload.get("region") or settings.default_region
    source_tz = payload.get("source_timezone") or tz_hdr or "UTC"
    metrics = payload.get("metrics", {})
    collector_status = payload.get("collector_status", "online")

    # Parse ISO 8601 UTC timestamp
    raw_ts = payload.get("timestamp")
    try:
        if raw_ts:
            event_time = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
        else:
            event_time = datetime.now(timezone.utc)
    except Exception:
        event_time = datetime.now(timezone.utc)

    repo = CentralRepository(db)

    # 1. Idempotency Check & Save
    created, record = repo.save_telemetry_idempotent(
        message_id=message_id,
        tenant_id=tenant_id,
        device_id=device_id,
        event_time=event_time,
        region=region,
        metrics=metrics,
        collector_status=collector_status,
        source_timezone=source_tz,
    )

    if not created:
        repo.record_delivery(tenant_id, is_duplicate=True)
        db.commit()
        response.status_code = status.HTTP_200_OK
        return {
            "status": "duplicate_ignored",
            "message_id": message_id,
            "detail": "Payload has already been ingested and acknowledged; duplicate discarded idempotently.",
        }

    repo.record_delivery(tenant_id, is_duplicate=False)

    # Upsert collector host info if available in payload
    repo.upsert_collector(
        tenant_id=tenant_id,
        device_id=device_id,
        hostname=payload.get("hostname") or "unknown-host",
        os_info=payload.get("os_info") or "Unknown OS",
        region=region,
        collector_cpu_overhead=payload.get("collector_cpu_overhead", 0.2),
        collector_ram_overhead=payload.get("collector_ram_overhead", 24.5),
        config_status=payload.get("config_status", "synced"),
    )

    # 2. Historical Baseline Query
    history = repo.get_telemetry_series(tenant_id=tenant_id, device_id=device_id, limit=settings.baseline_window_samples)

    # 3. Dynamic Anomaly Detection
    is_anomaly, contributing = AnomalyDetector.evaluate(current_metrics=metrics, history=history)
    
    if is_anomaly:
        record.is_anomaly = True
        record.anomaly_signals = json.dumps([s["signal"] for s in contributing])

        # 4. Multi-Signal Alert Correlation
        incident_data = EventCorrelator.correlate(tenant_id, device_id, contributing)
        if incident_data:
            # 5. Explainable AIOps Recommendation Generation
            rec_bundle = ExplainableRecommender.build_recommendation(incident_data, contributing)

            # Store / Deduplicate Incident within 120s cooldown window
            is_new, inc = repo.get_or_update_incident_deduped(
                tenant_id=tenant_id,
                device_id=device_id,
                title=incident_data["title"],
                category=incident_data["category"],
                severity=incident_data["severity"],
                root_cause=incident_data["root_cause"],
                explanation=rec_bundle["narrative"],
                confidence_score=incident_data["confidence_score"],
                contributing_signals=contributing,
                cooldown_seconds=120,
            )

            # Propose Safe Autonomous Ops Remediation Action (replaces / updates pending action)
            repo.create_remediation(
                incident_id=inc.id,
                tenant_id=tenant_id,
                action_type=rec_bundle["action_type"],
                title=rec_bundle["action_title"],
                description=rec_bundle["action_desc"],
                rollback_plan=rec_bundle["rollback_plan"],
            )

    # 6. Evaluate Four-State Health
    collector = repo.get_collector(tenant_id, device_id)
    if collector:
        health_state, health_reason = HealthClassifier.evaluate_node(
            collector,
            latest_metrics=metrics,
            has_active_critical_incident=is_anomaly and any(s.get("severity") == "critical" for s in contributing),
        )
        repo.update_collector_health(tenant_id, device_id, health_state, health_reason, status="online")

    db.commit()
    response.status_code = status.HTTP_201_CREATED
    return {
        "status": "received",
        "message_id": message_id,
        "tenant_id": tenant_id,
        "device_id": device_id,
        "is_anomaly": is_anomaly,
        "health_state": collector.health_state if collector else "Good",
    }
