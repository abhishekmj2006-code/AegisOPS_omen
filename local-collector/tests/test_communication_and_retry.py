"""Tests for communication, exponential backoff, idempotency, and invalid responses."""

import uuid
import pytest
from config.settings import Settings
from database.storage import DatabaseManager
from database.offline_queue import OfflineQueue
from communication.api_client import APIClient
from communication.connection_manager import ConnectionManager
from communication.retry_manager import RetryManager


@pytest.fixture
def mock_setup(tmp_path):
    settings = Settings(
        backend_url="http://127.0.0.1:9999", # Non-existent port for error simulation
        tenant_id="TENANT_TEST",
        device_id="DEVICE_TEST",
    )
    db_mgr = DatabaseManager(str(tmp_path / "comm_test.db"))
    queue = OfflineQueue(db_mgr)
    api_client = APIClient(settings, timeout=1.0)
    conn_mgr = ConnectionManager(settings, api_client)
    retry_mgr = RetryManager(queue, api_client, conn_mgr, base_delay=1.0, max_delay=10.0)
    return {
        "settings": settings,
        "queue": queue,
        "api_client": api_client,
        "conn_mgr": conn_mgr,
        "retry_mgr": retry_mgr,
    }


def test_exponential_backoff_calculation(mock_setup):
    """Verify exponential backoff calculation and cap."""
    retry_mgr = mock_setup["retry_mgr"]

    delay_0 = retry_mgr.calculate_backoff(0)
    delay_1 = retry_mgr.calculate_backoff(1)
    delay_2 = retry_mgr.calculate_backoff(2)
    delay_10 = retry_mgr.calculate_backoff(10)

    # Must increase exponentially
    assert delay_0 < delay_1 < delay_2
    # Must be bounded by max_delay + jitter
    assert delay_10 <= 15.0


def test_api_client_connection_error_handling(mock_setup):
    """When backend is offline, API client must return clean error without throwing exception."""
    api_client = mock_setup["api_client"]
    success, status_code, err = api_client.check_health()
    assert success is False
    assert status_code == 0
    assert "Connection" in err or "unreachable" in err or "refused" in err

    payload = {"message_id": str(uuid.uuid4())}
    success, status_code, err = api_client.send_metrics(payload)
    assert success is False
    assert status_code == 0


def test_retry_manager_offline_handling(mock_setup):
    """When transmission fails due to offline backend, message remains pending in queue."""
    queue = mock_setup["queue"]
    retry_mgr = mock_setup["retry_mgr"]

    msg_id = str(uuid.uuid4())
    payload = {
        "message_id": msg_id,
        "tenant_id": "TENANT_TEST",
        "device_id": "DEVICE_TEST",
        "timestamp": "2026-11-20T10:00:00Z",
        "region": "ap-south-1",
        "collector_status": "online",
        "metrics": {
            "cpu_usage": 10.0,
            "ram_usage": 20.0,
            "disk_usage": 30.0,
            "network_latency_ms": 1.0,
            "packet_loss_percent": 0.0,
            "failed_login_count": 0,
        },
    }
    queue.enqueue(payload)

    # Process queue while backend is unreachable
    sent, failed = retry_mgr.process_pending_queue()
    assert sent == 0
    assert failed == 1

    # Verify message was not deleted
    pending = queue.get_pending_messages()
    assert len(pending) == 1
    assert pending[0]["message_id"] == msg_id
    assert pending[0]["retry_count"] == 1
