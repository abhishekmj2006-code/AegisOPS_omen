"""Tests for system, disk, network, login collectors, and stream adapter."""

import os
import pytest
from collector.system_monitor import SystemMonitor
from collector.disk_monitor import DiskMonitor
from collector.network_monitor import NetworkMonitor
from collector.login_monitor import LoginMonitor
from collector.stream_adapter import TelemetryStreamAdapter


def test_system_monitor_metrics():
    """Verify CPU and RAM metrics collection and boundaries."""
    monitor = SystemMonitor()
    metrics = monitor.collect_metrics()

    assert "cpu_usage" in metrics
    assert "ram_usage" in metrics
    assert "ram_total_gb" in metrics
    assert "ram_available_gb" in metrics

    assert 0.0 <= metrics["cpu_usage"] <= 100.0
    assert 0.0 <= metrics["ram_usage"] <= 100.0
    assert metrics["ram_total_gb"] >= 0.0
    assert metrics["ram_available_gb"] >= 0.0


def test_system_info():
    """Verify host metadata retrieval."""
    monitor = SystemMonitor()
    info = monitor.get_system_info()

    assert "os" in info
    assert "architecture" in info
    assert "hostname" in info
    assert len(info["os"]) > 0


def test_disk_monitor_metrics():
    """Verify disk utilization and rate calculations."""
    monitor = DiskMonitor()
    metrics = monitor.collect_metrics()

    assert "disk_usage" in metrics
    assert "disk_read_mbs" in metrics
    assert "disk_write_mbs" in metrics

    assert 0.0 <= metrics["disk_usage"] <= 100.0
    assert metrics["disk_read_mbs"] >= 0.0
    assert metrics["disk_write_mbs"] >= 0.0


def test_network_monitor_throughput_and_socket_probe():
    """Verify network stats, TCP latency fallback and packet loss computation."""
    monitor = NetworkMonitor(target_host="127.0.0.1", target_port=9)
    metrics = monitor.collect_metrics()

    assert "network_upload_kbps" in metrics
    assert "network_download_kbps" in metrics
    assert "network_latency_ms" in metrics
    assert "packet_loss_percent" in metrics

    assert metrics["network_upload_kbps"] >= 0.0
    assert metrics["network_download_kbps"] >= 0.0
    assert 0.0 <= metrics["packet_loss_percent"] <= 100.0


def test_login_monitor_sliding_window_and_threat_level():
    """Verify failed login tracking, 60s sliding window, and local threat levels."""
    monitor = LoginMonitor(window_seconds=60.0)
    monitor.reset_counter()
    
    # 0 failed logins: nominal threat level
    nominal = monitor.collect_login_metrics()
    assert nominal["security_threat_level"] == "nominal"

    # Inject 1 failed login: elevated threat level
    monitor.inject_test_failed_login(1)
    elevated = monitor.collect_login_metrics()
    assert elevated["failed_login_count"] >= 1
    assert elevated["security_threat_level"] == "elevated"

    # Inject 2 more (total 3): critical threat level
    monitor.inject_test_failed_login(2)
    critical = monitor.collect_login_metrics()
    assert critical["failed_login_count"] >= 3
    assert critical["security_threat_level"] == "critical"

    monitor.reset_counter()
    assert monitor.collect_login_metrics()["failed_login_count"] == 0


def test_stream_adapter_ndjson_and_simulation():
    """Verify stream adapter external stream ingestion and simulation harness."""
    adapter = TelemetryStreamAdapter(mode="HOST_SYSTEM")
    assert adapter.mode == "HOST_SYSTEM"

    adapter.set_mode("SIMULATED_STREAM")
    assert adapter.mode == "SIMULATED_STREAM"

    # Test NDJSON parsing
    ndjson_data = '{"source": "test_agent", "cpu": 45.0}\n{"source": "test_agent", "cpu": 55.0}\n'
    loaded = adapter.load_ndjson_string(ndjson_data)
    assert loaded == 2

    # Test simulation harness generators
    poisoned = adapter.generate_poisoned_log_event()
    assert "password=" in poisoned["raw_auth_log"]
    assert "aws_secret_key" in poisoned

    spike = adapter.generate_network_spike_event()
    assert spike["network_latency_ms"] > 100.0
    assert spike["packet_loss_percent"] > 3.0

    ooo = adapter.generate_out_of_order_events()
    assert len(ooo) == 3
