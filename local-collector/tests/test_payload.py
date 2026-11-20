"""Tests for outgoing payload structure, validation, UUIDs, and timestamps."""

import uuid
import pytest
from pydantic import ValidationError

from models.metric import SystemMetrics
from models.payload import OutgoingPayload
from security.validator import PayloadValidator
from utils.timestamps import get_iso_utc_now, format_iso_utc, get_utc_now


def test_valid_outgoing_payload():
    """Verify that a compliant payload passes strict validation."""
    payload_data = {
        "message_id": str(uuid.uuid4()),
        "tenant_id": "TENANT_001",
        "device_id": "DEVICE_001",
        "timestamp": get_iso_utc_now(),
        "region": "ap-south-1",
        "collector_status": "online",
        "metrics": {
            "cpu_usage": 45.2,
            "ram_usage": 67.8,
            "disk_usage": 80.0,
            "network_latency_ms": 15.5,
            "packet_loss_percent": 0.0,
            "failed_login_count": 0,
        },
    }
    is_valid, model, errors = PayloadValidator.validate_outgoing_payload(payload_data)
    assert is_valid is True
    assert model is not None
    assert errors == []
    assert model.tenant_id == "TENANT_001"


def test_rejection_of_unexpected_top_level_fields():
    """Verify that unexpected extra top-level fields are strictly rejected (extra='forbid')."""
    payload_data = {
        "message_id": str(uuid.uuid4()),
        "tenant_id": "TENANT_001",
        "device_id": "DEVICE_001",
        "timestamp": get_iso_utc_now(),
        "region": "ap-south-1",
        "collector_status": "online",
        "unexpected_extra_field": "hacker_data",
        "metrics": {
            "cpu_usage": 45.2,
            "ram_usage": 67.8,
            "disk_usage": 80.0,
            "network_latency_ms": 15.5,
            "packet_loss_percent": 0.0,
        },
    }
    is_valid, model, errors = PayloadValidator.validate_outgoing_payload(payload_data)
    assert is_valid is False
    assert model is None
    assert any("unexpected_extra_field" in e for e in errors)


def test_rejection_of_unexpected_metrics_fields():
    """Verify that unexpected fields in metrics dict are strictly rejected."""
    payload_data = {
        "message_id": str(uuid.uuid4()),
        "tenant_id": "TENANT_001",
        "device_id": "DEVICE_001",
        "timestamp": get_iso_utc_now(),
        "region": "ap-south-1",
        "collector_status": "online",
        "metrics": {
            "cpu_usage": 45.2,
            "ram_usage": 67.8,
            "disk_usage": 80.0,
            "network_latency_ms": 15.5,
            "packet_loss_percent": 0.0,
            "raw_user_log_content": "cat /etc/shadow",
        },
    }
    is_valid, model, errors = PayloadValidator.validate_outgoing_payload(payload_data)
    assert is_valid is False
    assert any("raw_user_log_content" in e for e in errors)


def test_uuid_validation():
    """Verify that message_id must be a valid UUID format."""
    payload_data = {
        "message_id": "invalid-non-uuid-string",
        "tenant_id": "TENANT_001",
        "device_id": "DEVICE_001",
        "timestamp": get_iso_utc_now(),
        "region": "ap-south-1",
        "collector_status": "online",
        "metrics": {
            "cpu_usage": 50.0,
            "ram_usage": 50.0,
            "disk_usage": 50.0,
            "network_latency_ms": 10.0,
            "packet_loss_percent": 0.0,
        },
    }
    is_valid, model, errors = PayloadValidator.validate_outgoing_payload(payload_data)
    assert is_valid is False
    assert any("message_id" in e for e in errors)


def test_utc_iso8601_timestamp_format():
    """Verify that timestamps are formatted in UTC with Z suffix."""
    iso_ts = get_iso_utc_now()
    assert iso_ts.endswith("Z")
    assert "T" in iso_ts

    dt = get_utc_now()
    formatted = format_iso_utc(dt)
    assert formatted.endswith("Z")
