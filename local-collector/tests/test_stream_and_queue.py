"""Tests for stream loading, offline queue pending prioritization, and source timezone handling."""

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone, timedelta
import pytest

from config.settings import Settings, get_system_timezone
from collector.stream_adapter import TelemetryStreamAdapter
from collector.collector_service import CollectorService
from database.storage import DatabaseManager
from database.offline_queue import OfflineQueue
from security.sanitizer import Sanitizer


def test_source_timezone_default_and_payload_preservation():
    """Verify that source_timezone detects host timezone and is preserved in outgoing wire payload."""
    detected_tz = get_system_timezone()
    assert detected_tz is not None and len(detected_tz) > 0

    settings = Settings(source_timezone="Asia/Kolkata")
    assert settings.source_timezone == "Asia/Kolkata"

    sanitizer = Sanitizer()
    raw_payload = {
        "message_id": str(uuid.uuid4()),
        "tenant_id": "TENANT_001",
        "device_id": "DEVICE_TZ_TEST",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "region": "ap-south-1",
        "source_timezone": "Asia/Kolkata",
        "collector_status": "online",
        "metrics": {
            "cpu_usage": 32.5,
            "ram_usage": 45.0,
            "disk_usage": 50.0,
            "network_latency_ms": 20.0,
            "packet_loss_percent": 0.0,
            "failed_login_count": 0,
        },
    }

    res = sanitizer.sanitize_payload(raw_payload)
    assert res.is_valid is True
    assert res.sanitized_data["source_timezone"] == "Asia/Kolkata"


def test_stream_adapter_load_file_json_and_ndjson():
    """Verify loading external JSON array and NDJSON telemetry stream files."""
    adapter = TelemetryStreamAdapter(mode="SIMULATED_STREAM")

    # 1. Test JSON Array file
    json_events = [
        {"cpu_usage": 45.0, "ram_usage": 60.0},
        {"cpu_usage": 52.0, "ram_usage": 62.0},
    ]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(json_events, f)
        json_file = f.name

    try:
        loaded_json = adapter.load_file(json_file)
        assert len(loaded_json) == 2
        assert loaded_json[0]["cpu_usage"] == 45.0
    finally:
        if os.path.exists(json_file):
            os.remove(json_file)

    # 2. Test NDJSON file
    with tempfile.NamedTemporaryFile("w", suffix=".ndjson", delete=False, encoding="utf-8") as f:
        f.write('{"cpu_usage": 77.0, "ram_usage": 80.0}\n')
        f.write('{"cpu_usage": 85.0, "ram_usage": 82.0}\n')
        f.write('{"cpu_usage": 91.0, "ram_usage": 84.0}\n')
        ndjson_file = f.name

    try:
        loaded_ndjson = adapter.load_file(ndjson_file)
        assert len(loaded_ndjson) == 3
        assert loaded_ndjson[2]["cpu_usage"] == 91.0
    finally:
        if os.path.exists(ndjson_file):
            os.remove(ndjson_file)


def test_collector_replay_stream_file():
    """Verify replaying external stream file through collector service sanitizer and offline queue."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as db_tmp:
        db_path = db_tmp.name

    settings = Settings(db_path=db_path)
    service = CollectorService(settings)

    # Poisoned stream file containing secrets + valid metrics
    events = [
        {
            "cpu_usage": 40.0,
            "ram_usage": 50.0,
            "injected_secret_password": "super_secret_123",
        },
        {
            "cpu_usage": 88.0,
            "ram_usage": 75.0,
            "api_key": "AKIA999SECRETKEYEXAMPLE",
        },
    ]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(events, f)
        stream_file = f.name

    try:
        count = service.replay_stream_file(stream_file)
        assert count == 2
        # Verify secrets were stripped
        assert service.total_sensitive_detected >= 2
        # Verify enqueued in offline queue
        stats = service.offline_queue.get_stats()
        assert stats["total"] >= 2
    finally:
        if os.path.exists(stream_file):
            try:
                os.remove(stream_file)
            except Exception:
                pass
        try:
            service.db_manager.engine.dispose()
            if os.path.exists(db_path):
                os.remove(db_path)
        except Exception:
            pass


def test_offline_queue_pending_first_newest_descending_ordering():
    """Verify that get_recent_messages prioritizes PENDING records and sorts by created_at DESC."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as db_tmp:
        db_path = db_tmp.name

    db_manager = DatabaseManager(db_path)
    queue = OfflineQueue(db_manager)

    try:
        # Enqueue 3 messages
        p1 = {"message_id": str(uuid.uuid4()), "data": "msg1"}
        p2 = {"message_id": str(uuid.uuid4()), "data": "msg2"}
        p3 = {"message_id": str(uuid.uuid4()), "data": "msg3"}

        queue.enqueue(p1)
        queue.enqueue(p2)
        queue.enqueue(p3)

        # Mark p1 and p3 as SENT, leave p2 as PENDING
        queue.mark_as_sent(p1["message_id"], "ack")
        queue.mark_as_sent(p3["message_id"], "ack")

        recent = queue.get_recent_messages(limit=10)
        assert len(recent) == 3

        # p2 is PENDING, so it MUST appear at index 0 (top of the table)
        assert recent[0]["message_id"] == p2["message_id"]
        assert recent[0]["status"] == "PENDING"
        # The remaining are SENT
        assert recent[1]["status"] == "SENT"
        assert recent[2]["status"] == "SENT"
    finally:
        try:
            db_manager.engine.dispose()
            if os.path.exists(db_path):
                os.remove(db_path)
        except Exception:
            pass
