"""Tests for SQLite database persistence and offline queue operations."""

import os
import uuid
import pytest
from database.storage import DatabaseManager
from database.offline_queue import OfflineQueue


@pytest.fixture
def temp_db(tmp_path):
    """Fixture providing a temporary SQLite database."""
    db_file = tmp_path / "test_queue.db"
    db_mgr = DatabaseManager(str(db_file))
    queue = OfflineQueue(db_mgr)
    return queue


def test_enqueue_and_fifo_retrieval(temp_db):
    """Messages enqueued must be retrievable in FIFO order."""
    msg1_id = str(uuid.uuid4())
    msg2_id = str(uuid.uuid4())

    payload1 = {
        "message_id": msg1_id,
        "tenant_id": "TENANT_001",
        "device_id": "DEV_01",
        "timestamp": "2026-11-20T10:00:00.000Z",
        "metrics": {"cpu_usage": 20.0},
    }
    payload2 = {
        "message_id": msg2_id,
        "tenant_id": "TENANT_001",
        "device_id": "DEV_01",
        "timestamp": "2026-11-20T10:00:05.000Z",
        "metrics": {"cpu_usage": 30.0},
    }

    temp_db.enqueue(payload1)
    temp_db.enqueue(payload2)

    pending = temp_db.get_pending_messages(limit=10)
    assert len(pending) == 2
    assert pending[0]["message_id"] == msg1_id
    assert pending[1]["message_id"] == msg2_id


def test_mark_as_sent_acknowledged(temp_db):
    """Once server acknowledges, message is marked SENT and removed from pending queue."""
    msg_id = str(uuid.uuid4())
    payload = {
        "message_id": msg_id,
        "tenant_id": "TENANT_001",
        "device_id": "DEV_01",
        "metrics": {"cpu_usage": 40.0},
    }
    temp_db.enqueue(payload)

    # Initial state: 1 pending
    stats_before = temp_db.get_stats()
    assert stats_before["pending"] == 1
    assert stats_before["sent"] == 0

    # Mark as sent
    success = temp_db.mark_as_sent(msg_id, ack_response="HTTP 201 Created")
    assert success is True

    # After acknowledgment: 0 pending, 1 sent
    stats_after = temp_db.get_stats()
    assert stats_after["pending"] == 0
    assert stats_after["sent"] == 1

    pending = temp_db.get_pending_messages()
    assert len(pending) == 0


def test_mark_as_failed_retains_message(temp_db):
    """Failed transmission attempts increment retry count but NEVER delete pending message."""
    msg_id = str(uuid.uuid4())
    payload = {
        "message_id": msg_id,
        "tenant_id": "TENANT_001",
        "device_id": "DEV_01",
        "metrics": {"cpu_usage": 50.0},
    }
    temp_db.enqueue(payload)

    # Mark failed
    temp_db.mark_as_failed(msg_id, error_message="HTTP 503 Backend Service Unavailable")

    # Record must still exist in pending queue for subsequent retry!
    pending = temp_db.get_pending_messages()
    assert len(pending) == 1
    assert pending[0]["message_id"] == msg_id
    assert pending[0]["retry_count"] == 1

    stats = temp_db.get_stats()
    assert stats["pending"] == 1
    assert stats["failed_attempts"] == 1
