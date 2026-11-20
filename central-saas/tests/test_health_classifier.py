"""Tests for Four-State Health Classification Engine."""

import pytest
from datetime import datetime, timezone, timedelta
from storage.models import CollectorNode
from aiops.health_classifier import HealthClassifier


def test_four_state_health_nominal_is_excellent():
    now = datetime.now(timezone.utc)
    node = CollectorNode(
        device_id="NODE_1",
        tenant_id="TENANT_001",
        last_heartbeat=now,
        last_metric_received=now,
    )
    metrics = {
        "cpu_usage": 15.0,
        "ram_usage": 40.0,
        "network_latency_ms": 12.0,
        "packet_loss_percent": 0.0,
        "failed_login_count": 0,
    }
    state, reason = HealthClassifier.evaluate_node(node, metrics)
    assert state == "Excellent"


def test_four_state_health_warning_is_fair():
    now = datetime.now(timezone.utc)
    node = CollectorNode(
        device_id="NODE_1",
        tenant_id="TENANT_001",
        last_heartbeat=now,
        last_metric_received=now,
    )
    metrics = {
        "cpu_usage": 78.0,  # Exceeds 75% warning
        "ram_usage": 40.0,
        "network_latency_ms": 12.0,
        "packet_loss_percent": 0.0,
    }
    state, reason = HealthClassifier.evaluate_node(node, metrics)
    assert state == "Fair"
    assert "Elevated CPU" in reason


def test_four_state_health_critical_is_poor():
    now = datetime.now(timezone.utc)
    node = CollectorNode(
        device_id="NODE_1",
        tenant_id="TENANT_001",
        last_heartbeat=now,
        last_metric_received=now,
    )
    metrics = {
        "cpu_usage": 94.0,  # Exceeds 90% critical
        "ram_usage": 40.0,
        "network_latency_ms": 12.0,
        "packet_loss_percent": 0.0,
    }
    state, reason = HealthClassifier.evaluate_node(node, metrics)
    assert state == "Poor"
    assert "Critical CPU" in reason


def test_four_state_health_stale_heartbeat_is_poor():
    # Heartbeat lost for >60s (offline detection)
    stale_time = datetime.now(timezone.utc) - timedelta(seconds=75)
    node = CollectorNode(
        device_id="NODE_1",
        tenant_id="TENANT_001",
        last_heartbeat=stale_time,
        last_metric_received=stale_time,
    )
    state, reason = HealthClassifier.evaluate_node(node, latest_metrics={})
    assert state == "Poor"
    assert "Heartbeat lost" in reason
