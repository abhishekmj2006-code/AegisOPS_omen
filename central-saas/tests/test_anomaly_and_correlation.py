"""Tests for Anomaly Detection, Correlation, and Explainable Recommendations."""

import pytest
from aiops.anomaly_detector import AnomalyDetector
from aiops.correlator import EventCorrelator
from aiops.recommender import ExplainableRecommender


def test_anomaly_detection_and_network_correlation():
    # Simulate network latency spike + packet loss
    metrics = {
        "cpu_usage": 20.0,
        "ram_usage": 40.0,
        "network_latency_ms": 135.0,
        "packet_loss_percent": 4.0,
        "failed_login_count": 0,
    }
    
    is_anomaly, contributing = AnomalyDetector.evaluate(current_metrics=metrics, history=[])
    assert is_anomaly is True
    assert len(contributing) >= 2

    # Multi-signal alert correlation
    incident = EventCorrelator.correlate("TENANT_001", "DEV_1", contributing)
    assert incident is not None
    assert incident["category"] == "Network"
    assert "Network Path Degradation" in incident["title"]
    assert incident["confidence_score"] >= 0.90

    # Explainable recommendation
    rec = ExplainableRecommender.build_recommendation(incident, contributing)
    assert "network_latency_ms" in rec["narrative"]
    assert "packet_loss_percent" in rec["narrative"]
    assert rec["action_type"] == "reroute_gateway"
    assert rec["rollback_plan"] is not None


def test_failed_login_security_correlation():
    metrics = {
        "cpu_usage": 20.0,
        "ram_usage": 40.0,
        "network_latency_ms": 15.0,
        "packet_loss_percent": 0.0,
        "failed_login_count": 6,  # Surge
    }
    is_anomaly, contributing = AnomalyDetector.evaluate(current_metrics=metrics, history=[])
    assert is_anomaly is True

    incident = EventCorrelator.correlate("TENANT_001", "DEV_1", contributing)
    assert incident is not None
    assert incident["category"] == "Security"
    assert "Authentication Failures" in incident["title"]
    assert incident["confidence_score"] == 0.98
