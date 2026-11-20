"""Tests for Google GenAI LLM Copilot Engine and Seamless Local Fallback."""

import json
from unittest.mock import patch, MagicMock
import pytest

from aiops.llm_engine import AIOpsLLMEngine, get_gemini_api_key


@pytest.fixture
def sample_metrics():
    return {
        "cpu_usage": 88.5,
        "ram_usage": 91.2,
        "disk_usage": 45.0,
        "network_latency_ms": 42.0,
        "packet_loss_percent": 0.0,
        "failed_login_count": 0,
    }


@pytest.fixture
def sample_contributing():
    return [
        {
            "signal": "cpu_usage",
            "current": 88.5,
            "baseline_mean": 22.0,
            "z_score": 3.8,
            "severity": "high",
        },
        {
            "signal": "ram_usage",
            "current": 91.2,
            "baseline_mean": 65.0,
            "z_score": 2.9,
            "severity": "high",
        },
    ]


def test_llm_engine_empty_signals():
    result = AIOpsLLMEngine.analyze(
        tenant_id="TENANT_001",
        device_id="DEV_TEST",
        current_metrics={},
        contributing_signals=[],
    )
    assert result is None


def test_llm_engine_fallback_when_no_api_key(sample_metrics, sample_contributing):
    # Ensure no API key in environment
    with patch("aiops.llm_engine.get_gemini_api_key", return_value=None):
        result = AIOpsLLMEngine.analyze(
            tenant_id="TENANT_001",
            device_id="DEV_001",
            current_metrics=sample_metrics,
            contributing_signals=sample_contributing,
        )

        assert result is not None
        assert "Host Compute Saturation" in result["title"]
        assert result["category"] == "Performance"
        assert result["severity"] in ["high", "critical"]
        assert result["confidence_score"] >= 0.90
        assert "Deterministic AIOps Statistical Engine" in result["ai_engine"]
        assert "Root Cause Diagnosis:" in result["explanation"]
        assert "Contributing Telemetry Signals:" in result["explanation"]
        assert result["action_title"] is not None
        assert result["rollback_plan"] is not None


def test_llm_engine_gemini_mocked_success(sample_metrics, sample_contributing):
    mock_gemini_response = {
        "root_cause": "Sustained Process Thread Exhaustion",
        "why_flagged": "CPU utilization surged to 88.5% and RAM allocation breached 91.2%, exceeding 2 standard deviations.",
        "contributing_signals": [
            "cpu_usage: Observed 88.5% vs Baseline 22.0% (+3.8σ)",
            "ram_usage: Observed 91.2% vs Baseline 65.0% (+2.9σ)",
        ],
        "confidence_score": 94,
        "recommended_action": "Throttle High-Priority Background Workers & Flush Caches",
        "why_this_action": "Dispatches safe non-intrusive runtime backoff signal to stabilize system compute footprint.",
        "ai_engine": "Google Gemini (gemini-2.5-flash)",
    }

    mock_response_obj = MagicMock()
    mock_response_obj.text = json.dumps(mock_gemini_response)

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response_obj

    with patch("aiops.llm_engine.get_gemini_api_key", return_value="AIzaSyMockTestKey123"):
        with patch("google.genai.Client", return_value=mock_client):
            result = AIOpsLLMEngine.analyze(
                tenant_id="TENANT_001",
                device_id="DEV_GEMINI",
                current_metrics=sample_metrics,
                contributing_signals=sample_contributing,
                collector_metadata={"region": "ap-south-1", "health_state": "Fair"},
            )

            assert result is not None
            assert result["root_cause"] == "Sustained Process Thread Exhaustion"
            assert result["confidence_score"] == 0.94
            assert result["ai_engine"] == "Google Gemini (gemini-2.5-flash)"
            assert result["action_title"] == "Throttle High-Priority Background Workers & Flush Caches"
            assert "AI Engine: Google Gemini (gemini-2.5-flash)" in result["explanation"]
            assert mock_client.models.generate_content.called


def test_llm_engine_gemini_api_error_seamless_fallback(sample_metrics, sample_contributing):
    # Simulate API connection error or timeout
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = TimeoutError("Gemini endpoint connection timed out (2000ms)")

    with patch("aiops.llm_engine.get_gemini_api_key", return_value="AIzaSyMockTestKey123"):
        with patch("google.genai.Client", return_value=mock_client):
            # Must NOT raise exception; should seamlessly return fallback
            result = AIOpsLLMEngine.analyze(
                tenant_id="TENANT_001",
                device_id="DEV_FALLBACK",
                current_metrics=sample_metrics,
                contributing_signals=sample_contributing,
            )

            assert result is not None
            assert "Deterministic AIOps Statistical Engine (Local Fallback)" in result["ai_engine"]
            assert result["confidence_score"] > 0
            assert "Root Cause Diagnosis:" in result["explanation"]
