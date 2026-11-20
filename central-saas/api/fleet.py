"""Collector Fleet Management API."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.orm import Session

from storage.database import get_db
from storage.repository import CentralRepository
from aiops.health_classifier import HealthClassifier
from saas_config.settings import settings

router = APIRouter(prefix="/api/v1/fleet", tags=["Fleet Management"])


@router.get("")
def list_fleet(
    tenant_id: str = Query("TENANT_001", description="Tenant isolation scope"),
    db: Session = Depends(get_db),
):
    """Retrieve all collector nodes for a tenant with live four-state health assessment."""
    repo = CentralRepository(db)
    nodes = repo.get_fleet_by_tenant(tenant_id)
    now = datetime.now(timezone.utc)

    fleet_data = []
    for node in nodes:
        # Check for offline timeout (>60s)
        if node.last_heartbeat:
            hb = node.last_heartbeat
            last_hb_utc = hb if hb.tzinfo else hb.replace(tzinfo=timezone.utc)
            delta = (now - last_hb_utc).total_seconds()
            if delta > settings.heartbeat_timeout_seconds:
                if node.health_state != "Poor":
                    repo.record_health_transition(
                        node.tenant_id, node.device_id, node.health_state, "Poor",
                        f"Collector offline: Heartbeat lost for {int(delta)}s (> {int(settings.heartbeat_timeout_seconds)}s)."
                    )
                node.status = "offline"
                node.health_state = "Poor"
                node.health_reason = f"Collector offline: Heartbeat lost for {int(delta)}s (> {int(settings.heartbeat_timeout_seconds)}s)."
        else:
            delta = 9999

        fleet_data.append({
            "device_id": node.device_id,
            "tenant_id": node.tenant_id,
            "hostname": node.hostname,
            "os_info": node.os_info,
            "architecture": node.architecture,
            "version": node.version,
            "region": node.region,
            "status": node.status,
            "health_state": node.health_state,
            "health_reason": node.health_reason,
            "collector_cpu_overhead": getattr(node, "collector_cpu_overhead", 0.2),
            "collector_ram_overhead": getattr(node, "collector_ram_overhead", 24.5),
            "config_status": getattr(node, "config_status", "synced"),
            "last_heartbeat": node.last_heartbeat.isoformat() if node.last_heartbeat else None,
            "seconds_since_heartbeat": round(delta, 1),
            "last_metric_received": node.last_metric_received.isoformat() if node.last_metric_received else None,
        })

    db.commit()
    return {
        "tenant_id": tenant_id,
        "total_nodes": len(fleet_data),
        "online_count": sum(1 for n in fleet_data if n["status"] == "online"),
        "nodes": fleet_data,
    }


@router.get("/transitions")
def get_transitions(
    tenant_id: str = Query("TENANT_001", description="Tenant boundary"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Retrieve historical health state transition log."""
    repo = CentralRepository(db)
    transitions = repo.get_health_transitions(tenant_id, limit=limit)
    return {
        "tenant_id": tenant_id,
        "transitions": [
            {
                "id": t.id,
                "device_id": t.device_id,
                "previous_state": t.previous_state,
                "new_state": t.new_state,
                "reason": t.reason,
                "timestamp": t.timestamp.isoformat() if t.timestamp else None,
            }
            for t in transitions
        ],
    }


@router.get("/sla")
def get_sla(
    tenant_id: str = Query("TENANT_001", description="Tenant boundary"),
    db: Session = Depends(get_db),
):
    """Retrieve real-time SLA metrics: collection latency, breach latency, delivery counts."""
    repo = CentralRepository(db)
    return {
        "tenant_id": tenant_id,
        **repo.get_sla_metrics(tenant_id),
    }


@router.get("/thresholds")
def get_thresholds():
    """Retrieve current operational health and anomaly thresholds."""
    return {
        "cpu_warning_threshold": settings.cpu_warning_threshold,
        "cpu_critical_threshold": settings.cpu_critical_threshold,
        "ram_warning_threshold": settings.ram_warning_threshold,
        "ram_critical_threshold": settings.ram_critical_threshold,
        "latency_warning_ms": settings.latency_warning_ms,
        "latency_critical_ms": settings.latency_critical_ms,
        "packet_loss_warning_percent": settings.packet_loss_warning_percent,
        "heartbeat_timeout_seconds": settings.heartbeat_timeout_seconds,
        "anomaly_z_score_threshold": settings.anomaly_z_score_threshold,
    }


@router.post("/thresholds")
def update_thresholds(updates: Dict[str, Any] = Body(...)):
    """Update operational health thresholds at runtime."""
    alias_map = {
        "cpu_warning": "cpu_warning_threshold",
        "cpu_critical": "cpu_critical_threshold",
        "ram_warning": "ram_warning_threshold",
        "ram_critical": "ram_critical_threshold",
        "latency_warning": "latency_warning_ms",
        "latency_critical": "latency_critical_ms",
        "packet_loss_warning": "packet_loss_warning_percent",
    }
    for key, val in updates.items():
        attr = alias_map.get(key, key)
        if hasattr(settings, attr):
            setattr(settings, attr, float(val))
    return {
        "status": "updated",
        "thresholds": get_thresholds(),
    }
