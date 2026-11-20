"""End-to-end integration test: Offline Queueing -> Network Outage -> Reconnection -> Idempotent Delivery."""

import uuid
from typing import Any, Dict, List, Set, Tuple
import pytest
from config.settings import Settings
from database.storage import DatabaseManager
from database.offline_queue import OfflineQueue
from communication.api_client import APIClient
from communication.connection_manager import ConnectionManager
from communication.retry_manager import RetryManager


class SimulatedBackendClient(APIClient):
    """Simulates central FastAPI backend state machine for offline queue and idempotency testing."""

    def __init__(self, settings: Settings, is_offline: bool = False) -> None:
        super().__init__(settings)
        self.is_offline = is_offline
        self.seen_message_ids: Set[str] = set()
        self.received_messages: List[Dict[str, Any]] = []

    def check_health(self) -> Tuple[bool, int, str]:
        if self.is_offline:
            return False, 0, "Backend unreachable: Connection refused"
        return True, 200, '{"status": "healthy", "service": "AegisCentralBackend"}'

    def send_metrics(self, payload: Dict[str, Any]) -> Tuple[bool, int, str]:
        if self.is_offline:
            return False, 0, "Backend unreachable: Connection refused"

        message_id = payload.get("message_id", "")
        if message_id in self.seen_message_ids:
            return True, 200, '{"status": "duplicate_ignored", "message": "Duplicate ignored"}'

        self.seen_message_ids.add(message_id)
        self.received_messages.append(payload)
        return True, 201, '{"status": "received", "message_id": "' + message_id + '"}'


def test_end_to_end_offline_recovery_and_idempotency(tmp_path):
    """
    Test scenario required by project specifications:
    1. Start collector and simulated backend.
    2. Send monitoring records (Message 1) -> Successfully delivered and acknowledged.
    3. Disconnect backend (is_offline = True).
    4. Generate additional records (Message 2 & Message 3).
    5. Verify that they are persistently stored in SQLite pending queue.
    6. Restart / reconnect the backend (is_offline = False).
    7. Verify that pending records are transmitted from offline queue and marked SENT.
    8. Verify that acknowledged records are not retransmitted unnecessarily.
    9. Verify server-side idempotency prevents duplicate processing when message_id is repeated.
    """
    settings = Settings(
        backend_url="http://mock.internal.test",
        tenant_id="TENANT_ENTERPRISE",
        device_id="DEVICE_AUDIT",
    )
    db_mgr = DatabaseManager(str(tmp_path / "e2e_test.db"))
    queue = OfflineQueue(db_mgr)
    simulated_backend = SimulatedBackendClient(settings, is_offline=False)
    conn_mgr = ConnectionManager(settings, simulated_backend)
    retry_mgr = RetryManager(queue, simulated_backend, conn_mgr)

    # Step 1 & 2: Start collector and backend, send Message 1
    msg1_id = str(uuid.uuid4())
    payload1 = {
        "message_id": msg1_id,
        "tenant_id": settings.tenant_id,
        "device_id": settings.device_id,
        "timestamp": "2026-11-20T10:00:00.000Z",
        "region": "ap-south-1",
        "collector_status": "online",
        "metrics": {
            "cpu_usage": 25.0,
            "ram_usage": 50.0,
            "disk_usage": 40.0,
            "network_latency_ms": 15.0,
            "packet_loss_percent": 0.0,
            "failed_login_count": 0,
        },
    }

    queue.enqueue(payload1)
    assert queue.get_stats()["pending"] == 1

    sent, failed = retry_mgr.process_pending_queue()
    assert sent == 1
    assert failed == 0
    assert queue.get_stats()["pending"] == 0
    assert queue.get_stats()["sent"] == 1
    assert len(simulated_backend.received_messages) == 1

    # Step 3: Disconnect backend
    simulated_backend.is_offline = True

    # Step 4: Generate additional records (Message 2 & Message 3)
    msg2_id = str(uuid.uuid4())
    msg3_id = str(uuid.uuid4())
    payload2 = dict(payload1, message_id=msg2_id)
    payload3 = dict(payload1, message_id=msg3_id)

    queue.enqueue(payload2)
    queue.enqueue(payload3)

    # Step 5: Verify that they are stored in SQLite
    stats_offline = queue.get_stats()
    assert stats_offline["pending"] == 2
    assert stats_offline["sent"] == 1

    # Attempt transmission during outage: must fail and keep messages in SQLite
    sent_offline, failed_offline = retry_mgr.process_pending_queue()
    assert sent_offline == 0
    assert queue.get_stats()["pending"] == 2

    # Step 6: Restart / reconnect the backend
    simulated_backend.is_offline = False

    # Step 7: Verify that pending records are transmitted and acknowledged
    sent_recovered, failed_recovered = retry_mgr.process_pending_queue()
    assert sent_recovered == 2
    assert failed_recovered == 0

    stats_final = queue.get_stats()
    assert stats_final["pending"] == 0
    assert stats_final["sent"] == 3
    assert len(simulated_backend.received_messages) == 3

    # Step 8: Verify that acknowledged records are not retransmitted unnecessarily
    sent_noop, failed_noop = retry_mgr.process_pending_queue()
    assert sent_noop == 0
    assert failed_noop == 0

    # Step 9: Verify Idempotency Contract
    # When sending a previously acknowledged message_id, backend acknowledges duplicate without double counting
    duplicate_success, status_code, resp_text = simulated_backend.send_metrics(payload1)
    assert duplicate_success is True
    assert status_code == 200
    assert "duplicate_ignored" in resp_text
    # Received message list still only has 3 unique messages
    assert len(simulated_backend.received_messages) == 3
