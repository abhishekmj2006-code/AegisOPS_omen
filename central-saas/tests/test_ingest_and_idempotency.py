"""Tests for Ingestion API, Bearer Token Auth, Idempotency, and Out-of-Order Handling."""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import Response, HTTPException

from storage.database import init_db, SessionLocal
from api.ingest import health_check, receive_heartbeat, receive_metrics, HeartbeatPayload
from api.incidents import get_telemetry_series


@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def test_health_check_endpoint(db_session):
    data = health_check(db=db_session)
    assert data["status"] == "healthy"
    assert "TENANT_001" in data["active_tenants"]


def test_token_authentication_enforcement(db_session):
    payload = HeartbeatPayload(
        device_id="TEST_DEVICE_01",
        tenant_id="TENANT_001",
        timestamp="2026-11-20T12:00:00Z",
    )
    # 1. Missing token -> Should raise 401
    with pytest.raises(HTTPException) as exc1:
        receive_heartbeat(payload=payload, authorization=None, x_tenant_id=None, x_device_id=None, db=db_session)
    assert exc1.value.status_code == 401

    # 2. Invalid token -> Should raise 401
    with pytest.raises(HTTPException) as exc2:
        receive_heartbeat(payload=payload, authorization="Bearer invalid_token_xyz", x_tenant_id=None, x_device_id=None, db=db_session)
    assert exc2.value.status_code == 401

    # 3. Valid token -> Should succeed (200 OK)
    data = receive_heartbeat(
        payload=payload,
        authorization="Bearer aegis_token_sec_9942",
        x_tenant_id=None,
        x_device_id=None,
        db=db_session,
    )
    assert data["status"] == "alive"
    assert data["device_id"] == "TEST_DEVICE_01"


def test_metrics_ingest_and_idempotency(db_session):
    msg_id = f"test-idemp-{uuid.uuid4()}"
    payload = {
        "message_id": msg_id,
        "tenant_id": "TENANT_001",
        "device_id": "TEST_DEVICE_01",
        "timestamp": "2026-11-20T12:00:00Z",
        "region": "ap-south-1",
        "source_timezone": "UTC",
        "metrics": {
            "cpu_usage": 25.4,
            "ram_usage": 45.0,
            "disk_usage": 60.0,
            "network_latency_ms": 15.2,
            "packet_loss_percent": 0.0,
            "failed_login_count": 0,
            "security_threat_level": "nominal",
        },
        "collector_status": "online",
    }

    # 1. First delivery: Should create new record (201 Created)
    resp1 = Response()
    d1 = receive_metrics(
        payload=payload,
        response=resp1,
        authorization="Bearer aegis_token_sec_9942",
        x_tenant_id=None,
        x_device_id=None,
        x_source_timezone=None,
        db=db_session,
    )
    assert resp1.status_code == 201
    assert d1["status"] == "received"
    assert d1["message_id"] == msg_id

    # 2. Second delivery (Duplicate retry after outage): Should acknowledge without duplication (200 OK)
    resp2 = Response()
    d2 = receive_metrics(
        payload=payload,
        response=resp2,
        authorization="Bearer aegis_token_sec_9942",
        x_tenant_id=None,
        x_device_id=None,
        x_source_timezone=None,
        db=db_session,
    )
    assert resp2.status_code == 200
    assert d2["status"] == "duplicate_ignored"
    assert d2["message_id"] == msg_id


def test_out_of_order_event_chronological_ordering(db_session):
    """Verifies that events arriving out-of-order are strictly ordered by event UTC time."""
    now = datetime.now(timezone.utc)
    t_past_15 = now - timedelta(minutes=15)
    t_past_5 = now - timedelta(minutes=5)
    t_now = now

    dev = f"DEV_ORDER_{uuid.uuid4().hex[:6]}"

    # Ingest intentionally backwards: now, then 15m ago, then 5m ago
    for ts, cpu in [(t_now, 90.0), (t_past_15, 30.0), (t_past_5, 60.0)]:
        resp = Response()
        receive_metrics(
            payload={
                "message_id": str(uuid.uuid4()),
                "tenant_id": "TENANT_001",
                "device_id": dev,
                "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S.000000Z"),
                "metrics": {"cpu_usage": cpu, "ram_usage": 40.0},
            },
            response=resp,
            authorization="Bearer aegis_token_sec_9942",
            db=db_session,
        )

    # Fetch time series
    series_res = get_telemetry_series(tenant_id="TENANT_001", device_id=dev, limit=10, db=db_session)
    series = series_res["series"]
    assert len(series) == 3

    # Verify strictly ordered by event_time ASC (30.0 at past_15, then 60.0 at past_5, then 90.0 at now)
    cpu_ordered = [s["cpu_usage"] for s in series]
    assert cpu_ordered == [30.0, 60.0, 90.0]
