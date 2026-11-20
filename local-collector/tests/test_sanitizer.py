"""Tests for data sanitization, allowlisting, and secret stripping."""

import pytest
from security.sanitizer import Sanitizer
from security.allowlist import ALLOWED_TOP_LEVEL_KEYS, ALLOWED_METRICS_KEYS


@pytest.fixture
def sanitizer():
    return Sanitizer()


def test_sanitize_clean_metrics(sanitizer):
    """Clean metrics with only approved keys should pass through unmodified."""
    raw = {
        "cpu_usage": 45.5,
        "ram_usage": 60.2,
        "disk_usage": 70.1,
        "network_latency_ms": 25.0,
        "packet_loss_percent": 0.0,
        "failed_login_count": 0,
    }
    sanitized, sens_count, removed = sanitizer.sanitize_metrics(raw)

    assert sens_count == 0
    assert len(removed) == 0
    assert sanitized["cpu_usage"] == 45.5
    assert sanitized["failed_login_count"] == 0


def test_sanitize_passwords_and_api_keys(sanitizer):
    """Sensitive field names such as password, token, api_key must be detected and removed."""
    poisoned = {
        "cpu_usage": 50.0,
        "ram_usage": 55.0,
        "disk_usage": 40.0,
        "network_latency_ms": 10.0,
        "packet_loss_percent": 0.0,
        "password": "SuperSecretPassword!",
        "api_key": "sk-proj-1234567890",
        "auth_token": "bearer eyJhbGciOiJIUzI1NiJ9",
        "private_key": "-----BEGIN RSA PRIVATE KEY-----...",
    }
    sanitized, sens_count, removed = sanitizer.sanitize_metrics(poisoned)

    # All sensitive keys must be removed
    assert sens_count == 4
    assert "password" not in sanitized
    assert "api_key" not in sanitized
    assert "auth_token" not in sanitized
    assert "private_key" not in sanitized

    # Approved metrics must be preserved
    assert sanitized["cpu_usage"] == 50.0
    assert sanitized["ram_usage"] == 55.0


def test_sanitize_secret_values_in_strings(sanitizer):
    """Values matching secret patterns (e.g. AWS access key, JWT) must be stripped even if key looks innocent."""
    poisoned = {
        "cpu_usage": 33.3,
        "ram_usage": 44.4,
        "disk_usage": 55.5,
        "network_latency_ms": 12.0,
        "packet_loss_percent": 0.0,
        "custom_note": "AKIAIOSFODNN7EXAMPLE",
        "session_cookie": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.do_not_leak",
    }
    sanitized, sens_count, removed = sanitizer.sanitize_metrics(poisoned)

    assert "custom_note" not in sanitized
    assert "session_cookie" not in sanitized
    assert sens_count >= 2


def test_sanitize_full_payload(sanitizer):
    """Full payload sanitization: detects unallowlisted top-level keys and validates output."""
    raw_payload = {
        "message_id": "c9bf9e57-1685-4c89-bafb-ff5af830be8a",
        "tenant_id": "TENANT_001",
        "device_id": "DEVICE_001",
        "timestamp": "2026-11-20T10:00:00.000000Z",
        "region": "ap-south-1",
        "collector_status": "online",
        "unauthorized_secret": "my_db_password_123",
        "metrics": {
            "cpu_usage": 15.0,
            "ram_usage": 20.0,
            "disk_usage": 30.0,
            "network_latency_ms": 5.0,
            "packet_loss_percent": 0.0,
            "internal_token": "token_xyz",
        },
    }
    result = sanitizer.sanitize_payload(raw_payload)

    assert result.is_valid is True
    assert result.status == "SANITIZED"
    assert result.sensitive_fields_detected >= 2
    assert "unauthorized_secret" not in result.sanitized_data
    assert "internal_token" not in result.sanitized_data["metrics"]
    assert result.sanitized_data["metrics"]["cpu_usage"] == 15.0


def test_sanitize_security_threat_level_preserved(sanitizer):
    """security_threat_level must be preserved as a valid string and not dropped."""
    raw = {
        "cpu_usage": 35.0,
        "ram_usage": 45.0,
        "disk_usage": 50.0,
        "network_latency_ms": 12.0,
        "packet_loss_percent": 0.0,
        "failed_login_count": 5,
        "security_threat_level": "elevated",
    }
    sanitized, sens_count, removed = sanitizer.sanitize_metrics(raw)
    assert sens_count == 0
    assert len(removed) == 0
    assert sanitized["failed_login_count"] == 5
    assert sanitized["security_threat_level"] == "elevated"
