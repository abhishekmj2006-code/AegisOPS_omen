"""Telemetry Stream Adapter for evaluation stream compatibility and test harnesses.

Supports switching between real host telemetry and simulated event streams,
including injection of secrets, network degradation, failed logins, out-of-order events, and duplicates.
"""

from datetime import datetime, timezone, timedelta
import json
from typing import Any, Dict, Generator, List, Optional
import uuid

from utils.logger import get_logger

logger = get_logger("StreamAdapter")


class TelemetryStreamAdapter:
    """Ingests and transforms external JSON/NDJSON streams or generates synthetic evaluation telemetry."""

    def __init__(self, mode: str = "HOST_SYSTEM") -> None:
        self.mode = mode  # "HOST_SYSTEM" or "SIMULATED_STREAM"
        self._custom_stream_queue: List[Dict[str, Any]] = []

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        logger.info(f"Telemetry stream adapter switched to: {self.mode}")

    def enqueue_raw_event(self, event: Dict[str, Any]) -> None:
        """Enqueue an incoming raw event from external JSON/NDJSON feed."""
        self._custom_stream_queue.append(event)

    def load_ndjson_string(self, ndjson_content: str) -> int:
        """Parse NDJSON lines from external source."""
        count = 0
        for line in ndjson_content.strip().splitlines():
            line = line.strip()
            if line:
                try:
                    data = json.loads(line)
                    self._custom_stream_queue.append(data)
                    count += 1
                except Exception as e:
                    logger.warning(f"Skipping malformed NDJSON line: {e}")
        return count

    def load_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Load and parse JSON array or NDJSON stream from a file."""
        events: List[Dict[str, Any]] = []
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            return events

        # 1. Attempt JSON array
        if content.startswith("[") and content.endswith("]"):
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            events.append(item)
                            self._custom_stream_queue.append(item)
                    logger.info(f"Loaded {len(events)} events from JSON array file: {file_path}")
                    return events
            except Exception as e:
                logger.debug(f"File content is not valid JSON array, attempting NDJSON lines: {e}")

        # 2. Attempt NDJSON lines
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                if isinstance(item, dict):
                    events.append(item)
                    self._custom_stream_queue.append(item)
            except Exception as e:
                logger.warning(f"Skipping malformed line in {file_path}: {e}")

        logger.info(f"Loaded {len(events)} events from NDJSON file: {file_path}")
        return events

    # -------------------------------------------------------------
    # Simulation Harness Methods for Evaluation Verification
    # -------------------------------------------------------------
    @staticmethod
    def generate_poisoned_log_event() -> Dict[str, Any]:
        """Injects passwords and API keys inside raw logs and top-level fields."""
        return {
            "raw_auth_log": "2026-11-20T12:00:00Z auth_daemon: User admin auth failed password='SuperSecretPassword99!'",
            "aws_secret_key": "AKIAIOSFODNN7EXAMPLEKEYSECRET",
            "api_bearer_token": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy_secret",
            "metrics.unapproved_secret_token": "secret_cookie_val_12345",
        }

    @staticmethod
    def generate_network_spike_event() -> Dict[str, Any]:
        """Generates latency spike (>100ms) and packet loss (>3%)."""
        return {
            "network_latency_ms": 145.0,
            "packet_loss_percent": 4.5,
        }

    @staticmethod
    def generate_failed_login_event(count: int = 5) -> Dict[str, Any]:
        """Simulates repeated authentication failures (Windows Event ID 4625)."""
        return {
            "event_id": 4625,
            "raw_audit_text": f"EventID 4625: An account failed to log on. Count={count}. User=Administrator",
            "injected_failed_logins": count,
        }

    @staticmethod
    def generate_out_of_order_events(base_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Generates 3 events intentionally created in reverse chronological order."""
        t = base_time or datetime.now(timezone.utc)
        return [
            {
                "message_id": str(uuid.uuid4()),
                "timestamp": (t - timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%S.000000Z"),
                "metrics": {"cpu_usage": 35.0, "ram_usage": 45.0, "network_latency_ms": 18.0},
                "order_tag": "PAST_15_MINS",
            },
            {
                "message_id": str(uuid.uuid4()),
                "timestamp": (t - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S.000000Z"),
                "metrics": {"cpu_usage": 55.0, "ram_usage": 50.0, "network_latency_ms": 25.0},
                "order_tag": "PAST_5_MINS",
            },
            {
                "message_id": str(uuid.uuid4()),
                "timestamp": t.strftime("%Y-%m-%dT%H:%M:%S.000000Z"),
                "metrics": {"cpu_usage": 75.0, "ram_usage": 60.0, "network_latency_ms": 40.0},
                "order_tag": "CURRENT",
            },
        ]
