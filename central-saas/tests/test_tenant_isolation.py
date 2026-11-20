"""Tests for Multi-Tenant Isolation and Data Separation (Direct Invocation)."""

import pytest
import uuid
from fastapi import Response

from storage.database import init_db, SessionLocal
from api.ingest import receive_metrics
from api.fleet import list_fleet
from api.incidents import get_telemetry_series


@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def test_strict_tenant_isolation(db_session):
    # Ingest metric for Tenant 1
    m1_id = f"tenant1-{uuid.uuid4()}"
    receive_metrics(
        payload={
            "message_id": m1_id,
            "tenant_id": "TENANT_001",
            "device_id": "DEVICE_ALPHA",
            "metrics": {"cpu_usage": 30.0, "ram_usage": 50.0},
        },
        response=Response(),
        authorization="Bearer aegis_token_sec_9942",
        x_tenant_id=None,
        x_device_id=None,
        db=db_session,
    )

    # Ingest metric for Tenant 2
    m2_id = f"tenant2-{uuid.uuid4()}"
    receive_metrics(
        payload={
            "message_id": m2_id,
            "tenant_id": "TENANT_002",
            "device_id": "DEVICE_BETA",
            "metrics": {"cpu_usage": 40.0, "ram_usage": 60.0},
        },
        response=Response(),
        authorization="Bearer aegis_token_sec_9942",
        x_tenant_id=None,
        x_device_id=None,
        db=db_session,
    )

    # Query Tenant 1 fleet: must only contain DEVICE_ALPHA
    res1 = list_fleet(tenant_id="TENANT_001", db=db_session)
    devs_t1 = [n["device_id"] for n in res1["nodes"]]
    assert "DEVICE_ALPHA" in devs_t1
    assert "DEVICE_BETA" not in devs_t1

    # Query Tenant 2 fleet: must only contain DEVICE_BETA
    res2 = list_fleet(tenant_id="TENANT_002", db=db_session)
    devs_t2 = [n["device_id"] for n in res2["nodes"]]
    assert "DEVICE_BETA" in devs_t2
    assert "DEVICE_ALPHA" not in devs_t2

    # Query Tenant 1 telemetry series: must not contain m2_id
    t_res1 = get_telemetry_series(tenant_id="TENANT_001", device_id=None, limit=50, db=db_session)
    m_ids_t1 = [s["message_id"] for s in t_res1["series"]]
    assert m1_id in m_ids_t1
    assert m2_id not in m_ids_t1
