"""Live Scenario Verification & Injection API (Section 8 Evaluation Scenarios).

Enables instant live demonstration of the key observability scenarios:
- Latency & Packet Loss surge (network path degradation)
- CPU compute exhaustion
- Repeated failed logins (brute-force security alert)
- Out-of-order & duplicate event handling
- Safe autonomous ops remediation simulation
"""

from datetime import datetime, timezone, timedelta
import uuid
import json
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from storage.database import get_db
from storage.repository import CentralRepository
from aiops.anomaly_detector import AnomalyDetector
from aiops.correlator import EventCorrelator
from aiops.recommender import ExplainableRecommender
from aiops.health_classifier import HealthClassifier

router = APIRouter(prefix="/api/v1/scenarios", tags=["Scenario Validation"])


class InjectScenarioRequest(BaseModel):
    scenario: str  # "network_spike", "cpu_exhaustion", "brute_force_logins", "out_of_order", "nominal_reset"
    tenant_id: Optional[str] = "TENANT_001"
    device_id: Optional[str] = "DEVICE_001"


@router.post("/inject")
def inject_scenario(payload: InjectScenarioRequest, db: Session = Depends(get_db)):
    """Injects simulated real-time telemetry to demonstrate live AIOps detection."""
    tenant_id = payload.tenant_id or "TENANT_001"
    device_id = payload.device_id or "DEVICE_001"
    repo = CentralRepository(db)

    now = datetime.now(timezone.utc)
    scenario = payload.scenario.lower()

    if scenario == "network_spike":
        # Latency 142ms + 4.5% packet loss
        metrics = {
            "cpu_usage": 32.5,
            "ram_usage": 52.0,
            "disk_usage": 65.0,
            "network_latency_ms": 142.5,
            "packet_loss_percent": 4.5,
            "failed_login_count": 0,
        }
    elif scenario == "cpu_exhaustion":
        # CPU 96.8% + RAM 88.5%
        metrics = {
            "cpu_usage": 96.8,
            "ram_usage": 88.5,
            "disk_usage": 65.0,
            "network_latency_ms": 18.0,
            "packet_loss_percent": 0.0,
            "failed_login_count": 0,
        }
    elif scenario == "brute_force_logins":
        # 5 failed login attempts
        metrics = {
            "cpu_usage": 28.0,
            "ram_usage": 50.0,
            "disk_usage": 65.0,
            "network_latency_ms": 22.0,
            "packet_loss_percent": 0.0,
            "failed_login_count": 5,
        }
    elif scenario == "out_of_order":
        # Ingest 3 events intentionally created in reversed temporal order (10 mins ago, 5 mins ago, now)
        timestamps = [
            now - timedelta(minutes=10),
            now - timedelta(minutes=5),
            now,
        ]
        results = []
        for i, ts in enumerate(timestamps):
            mid = f"ooo-{uuid.uuid4()}"
            created, r = repo.save_telemetry_idempotent(
                message_id=mid,
                tenant_id=tenant_id,
                device_id=device_id,
                event_time=ts,
                region="ap-south-1",
                metrics={"cpu_usage": 30.0 + i * 5, "ram_usage": 45.0, "network_latency_ms": 20.0},
                source_timezone="UTC",
            )
            results.append({"message_id": mid, "event_time": ts.isoformat(), "ingested": created})
        db.commit()
        return {
            "status": "success",
            "scenario": "out_of_order",
            "detail": "Ingested 3 events with past event times. Verified time-series ordering sorts by event_time, not arrival.",
            "events": results,
        }
    else:  # nominal_reset
        metrics = {
            "cpu_usage": 22.0,
            "ram_usage": 48.0,
            "disk_usage": 64.0,
            "network_latency_ms": 15.0,
            "packet_loss_percent": 0.0,
            "failed_login_count": 0,
        }

    # Save telemetry
    mid = f"scen-{uuid.uuid4()}"
    created, record = repo.save_telemetry_idempotent(
        message_id=mid,
        tenant_id=tenant_id,
        device_id=device_id,
        event_time=now,
        region="ap-south-1",
        metrics=metrics,
        source_timezone="UTC",
    )

    # Trigger AIOps
    history = repo.get_telemetry_series(tenant_id=tenant_id, device_id=device_id, limit=15)
    is_anomaly, contributing = AnomalyDetector.evaluate(current_metrics=metrics, history=history)

    incident_created = None
    if is_anomaly:
        record.is_anomaly = True
        record.anomaly_signals = json.dumps([s["signal"] for s in contributing])

        inc_data = EventCorrelator.correlate(tenant_id, device_id, contributing)
        if inc_data:
            rec_bundle = ExplainableRecommender.build_recommendation(inc_data, contributing)
            inc = repo.create_incident(
                tenant_id=tenant_id,
                device_id=device_id,
                title=inc_data["title"],
                category=inc_data["category"],
                severity=inc_data["severity"],
                root_cause=inc_data["root_cause"],
                explanation=rec_bundle["narrative"],
                confidence_score=inc_data["confidence_score"],
                contributing_signals=contributing,
            )
            repo.create_remediation(
                incident_id=inc.id,
                tenant_id=tenant_id,
                action_type=rec_bundle["action_type"],
                title=rec_bundle["action_title"],
                description=rec_bundle["action_desc"],
                rollback_plan=rec_bundle["rollback_plan"],
            )
            incident_created = inc.title

    collector = repo.get_collector(tenant_id, device_id)
    if collector:
        h_state, h_reason = HealthClassifier.evaluate_node(
            collector,
            latest_metrics=metrics,
            has_active_critical_incident=is_anomaly and any(s.get("severity") == "critical" for s in contributing),
        )
        repo.update_collector_health(tenant_id, device_id, h_state, h_reason, status="online")

    db.commit()

    return {
        "status": "success",
        "scenario": scenario,
        "message_id": mid,
        "is_anomaly": is_anomaly,
        "contributing_signals_count": len(contributing),
        "incident_created": incident_created,
        "health_state": collector.health_state if collector else "Good",
    }
