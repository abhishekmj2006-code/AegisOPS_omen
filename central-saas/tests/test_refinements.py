"""Tests for incident deduplication, operational floors, SLA reliability, and transition logging."""

from datetime import datetime, timezone, timedelta
import uuid
import pytest
from fastapi import Response
from sqlalchemy.orm import Session

from aiops.anomaly_detector import AnomalyDetector
from aiops.health_classifier import HealthClassifier
from api.ingest import receive_metrics
from api.fleet import list_fleet, get_sla, get_transitions, get_thresholds, update_thresholds
from storage.repository import CentralRepository
from storage.models import TelemetryRecord
from storage.database import init_db, SessionLocal


@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def test_anomaly_operational_floors_suppress_low_usage_spikes():
    """Verify that low baseline jumps (e.g. 5% -> 18% CPU) do NOT trigger false alarms.
    
    Minimum operational floor for CPU is 60.0%, and for RAM is 75.0%.
    """
    # 15 samples of 5% CPU idle baseline
    history = [
        TelemetryRecord(
            message_id=str(uuid.uuid4()),
            tenant_id="TENANT_001",
            device_id="DEV_FLOOR",
            event_time=datetime.now(timezone.utc) - timedelta(seconds=i * 5),
            cpu_usage=5.0,
            ram_usage=30.0,
            network_latency_ms=10.0,
            packet_loss_percent=0.0,
        )
        for i in range(15)
    ]

    # Sudden jump to 18% CPU (large relative jump / high Z-score, but far below 60% operational floor)
    metrics_jump = {
        "cpu_usage": 18.0,
        "ram_usage": 35.0,
        "network_latency_ms": 12.0,
        "packet_loss_percent": 0.0,
    }

    is_anomaly, signals = AnomalyDetector.evaluate(metrics_jump, history)
    assert is_anomaly is False
    assert len(signals) == 0

    # Sudden jump to 65% RAM (below 75% operational floor)
    metrics_ram_jump = {
        "cpu_usage": 8.0,
        "ram_usage": 65.0,
        "network_latency_ms": 12.0,
        "packet_loss_percent": 0.0,
    }
    is_anomaly_ram, signals_ram = AnomalyDetector.evaluate(metrics_ram_jump, history)
    assert is_anomaly_ram is False
    assert len(signals_ram) == 0

    # Spike above 60% CPU (e.g. 92% CPU) MUST trigger an anomaly
    metrics_high_cpu = {
        "cpu_usage": 92.0,
        "ram_usage": 35.0,
        "network_latency_ms": 12.0,
        "packet_loss_percent": 0.0,
    }
    is_anomaly_high, signals_high = AnomalyDetector.evaluate(metrics_high_cpu, history)
    assert is_anomaly_high is True
    assert any(s["signal"] == "cpu_usage" for s in signals_high)


def test_incident_deduplication_and_cooldown(db_session: Session):
    """Verify that consecutive anomalies within 120s cooldown update the existing incident in-place."""
    unique_suffix = uuid.uuid4().hex[:8]
    tenant_id = f"TENANT_DEDUP_{unique_suffix}"
    device_id = f"DEV_DEDUP_{unique_suffix}"
    repo = CentralRepository(db_session)
    repo.ensure_tenant(tenant_id, region="ap-south-1")

    # Ingest 15 baseline samples of 15ms latency
    for i in range(15):
        receive_metrics(
            payload={
                "message_id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "device_id": device_id,
                "timestamp": (datetime.now(timezone.utc) - timedelta(seconds=100 - i * 5)).isoformat(),
                "metrics": {
                    "cpu_usage": 20.0,
                    "ram_usage": 30.0,
                    "network_latency_ms": 15.0,
                    "packet_loss_percent": 0.0,
                },
            },
            response=Response(),
            authorization="Bearer aegis_token_sec_9942",
            x_tenant_id=None,
            x_device_id=None,
            db=db_session,
        )

    # First spike: 180ms latency -> creates first incident
    m1_id = str(uuid.uuid4())
    receive_metrics(
        payload={
            "message_id": m1_id,
            "tenant_id": tenant_id,
            "device_id": device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                "cpu_usage": 20.0,
                "ram_usage": 30.0,
                "network_latency_ms": 180.0,
                "packet_loss_percent": 4.0,
            },
        },
        response=Response(),
        authorization="Bearer aegis_token_sec_9942",
        x_tenant_id=None,
        x_device_id=None,
        db=db_session,
    )

    incidents_first = repo.get_active_incidents(tenant_id)
    assert len(incidents_first) == 1
    inc1 = incidents_first[0]
    assert inc1.occurrence_count == 1
    orig_incident_id = inc1.id

    # Second spike 5 seconds later: 195ms latency -> within 120s cooldown window
    m2_id = str(uuid.uuid4())
    receive_metrics(
        payload={
            "message_id": m2_id,
            "tenant_id": tenant_id,
            "device_id": device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                "cpu_usage": 20.0,
                "ram_usage": 30.0,
                "network_latency_ms": 195.0,
                "packet_loss_percent": 4.5,
            },
        },
        response=Response(),
        authorization="Bearer aegis_token_sec_9942",
        x_tenant_id=None,
        x_device_id=None,
        db=db_session,
    )

    incidents_second = repo.get_active_incidents(tenant_id)
    # MUST still be exactly 1 incident (deduplicated in-place, not spammed)
    assert len(incidents_second) == 1
    inc2 = incidents_second[0]
    assert inc2.id == orig_incident_id
    assert inc2.occurrence_count == 2
    assert inc2.last_seen_at is not None

    # Remediation actions must not be duplicated
    open_remediations = repo.get_open_remediations(tenant_id)
    # Exactly one remediation plan for this incident
    actions_for_inc = [a for a in open_remediations if a.incident_id == orig_incident_id]
    assert len(actions_for_inc) == 1


def test_health_state_transition_logging(db_session: Session):
    """Verify that transitioning node health states records an audit log entry."""
    suffix = uuid.uuid4().hex[:8]
    tenant_id = f"TENANT_TRANS_{suffix}"
    device_id = f"DEV_TRANS_{suffix}"
    repo = CentralRepository(db_session)
    repo.ensure_tenant(tenant_id, region="ap-south-1")

    # Initial node creation in Excellent state
    repo.upsert_collector(tenant_id, device_id, hostname="host-trans", os_info="Linux 6.1")
    repo.update_collector_health(tenant_id, device_id, "Excellent", "All nominal", status="online")
    db_session.commit()

    # Transition to Poor state
    repo.update_collector_health(tenant_id, device_id, "Poor", "SLA heartbeat timeout exceeded (60s)", status="offline")
    db_session.commit()

    transitions_res = get_transitions(tenant_id=tenant_id, limit=10, db=db_session)
    assert len(transitions_res["transitions"]) >= 1
    latest_trans = transitions_res["transitions"][0]
    assert latest_trans["device_id"] == device_id
    assert latest_trans["previous_state"] == "Excellent"
    assert latest_trans["new_state"] == "Poor"
    assert "heartbeat timeout" in latest_trans["reason"]


def test_sla_delivery_reliability_panel_metrics(db_session: Session):
    """Verify SLA calculation for collection latency, breach latency, and duplicate detection."""
    suffix = uuid.uuid4().hex[:8]
    tenant_id = f"TENANT_SLA_{suffix}"
    repo = CentralRepository(db_session)
    repo.ensure_tenant(tenant_id, region="ap-south-1")

    # Record delivery statistics
    repo.record_delivery(tenant_id, is_duplicate=False)
    repo.record_delivery(tenant_id, is_duplicate=False)
    repo.record_delivery(tenant_id, is_duplicate=True)
    db_session.commit()

    sla_data = repo.get_sla_metrics(tenant_id)
    assert sla_data["unique_payloads_received"] == 2
    assert sla_data["duplicate_payloads_ignored"] == 1
    assert sla_data["collection_latency_status"] == "MET"
    assert sla_data["breach_latency_status"] == "MET"

    # API endpoint check
    res = get_sla(tenant_id=tenant_id, db=db_session)
    assert res["unique_payloads_received"] == 2
    assert res["duplicate_payloads_ignored"] == 1


def test_configurable_health_thresholds_api(db_session: Session):
    """Verify reading and updating dynamic health thresholds."""
    initial = get_thresholds()
    assert initial["cpu_critical_threshold"] >= 80.0

    update_res = update_thresholds({
        "cpu_warning": 65.0,
        "cpu_critical": 88.0,
        "ram_warning": 75.0,
        "ram_critical": 92.0,
        "latency_warning": 120.0,
        "latency_critical": 300.0,
        "packet_loss_warning": 3.0,
    })
    assert update_res["status"] == "updated"
    assert update_res["thresholds"]["cpu_warning_threshold"] == 65.0
    assert update_res["thresholds"]["cpu_critical_threshold"] == 88.0
