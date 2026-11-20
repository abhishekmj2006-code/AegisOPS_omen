"""Four-State Health Evaluation Engine.

Classifies monitored node health into:
- Excellent: Healthy. Collectors reporting; metrics within nominal baselines.
- Good: Normal. Minor deviations with no significant service impact.
- Fair: Needs attention. Elevated latency, resource use, packet loss, or stale data.
- Poor: Critical. Collector unavailable (heartbeat > 60s), severe service degradation, or security event.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from storage.models import CollectorNode, utc_now
from saas_config.settings import settings


def to_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class HealthClassifier:
    """Classifies collector node health with configurable thresholds and stale-data downgrades."""

    @staticmethod
    def evaluate_node(
        collector: CollectorNode,
        latest_metrics: Dict[str, Any],
        has_active_critical_incident: bool = False,
    ) -> Tuple[str, str]:
        """Evaluates health state and returns (state, reason)."""
        now = utc_now()

        # 1. Stale Heartbeat Check (Offline detection)
        if collector.last_heartbeat:
            hb_utc = to_utc(collector.last_heartbeat)
            hb_delta = (now - hb_utc).total_seconds()
            if hb_delta > settings.heartbeat_timeout_seconds:
                return "Poor", f"Collector offline: Heartbeat lost for {int(hb_delta)}s (> {int(settings.heartbeat_timeout_seconds)}s threshold)."

        # 2. Stale Telemetry Check
        if collector.last_metric_received:
            met_utc = to_utc(collector.last_metric_received)
            met_delta = (now - met_utc).total_seconds()
            if met_delta > settings.stale_data_seconds:
                return "Fair", f"Telemetry stale: No new metrics received for {int(met_delta)}s."

        # 3. Active Incident Check
        if has_active_critical_incident:
            return "Poor", "Active critical incident detected on host."

        if not latest_metrics:
            return "Good", "Collector online; awaiting baseline metrics."

        cpu = float(latest_metrics.get("cpu_usage", 0.0))
        ram = float(latest_metrics.get("ram_usage", 0.0))
        latency = float(latest_metrics.get("network_latency_ms", 0.0))
        loss = float(latest_metrics.get("packet_loss_percent", 0.0))
        failed_logins = int(latest_metrics.get("failed_login_count", 0))

        # 4. Critical (Poor) Checks
        if cpu >= settings.cpu_critical_threshold:
            return "Poor", f"Critical CPU saturation: {cpu:.1f}% exceeds {settings.cpu_critical_threshold:.0f}% limit."
        if ram >= settings.ram_critical_threshold:
            return "Poor", f"Critical memory pressure: {ram:.1f}% exceeds {settings.ram_critical_threshold:.0f}% limit."
        if latency >= settings.latency_critical_ms:
            return "Poor", f"Severe network latency: {latency:.1f}ms exceeds {settings.latency_critical_ms:.0f}ms."
        if loss >= settings.packet_loss_critical_percent:
            return "Poor", f"Severe packet loss: {loss:.1f}% exceeds {settings.packet_loss_critical_percent:.0f}% limit."
        if failed_logins >= settings.failed_logins_incident_threshold:
            return "Poor", f"Security Alert: {failed_logins} repeated failed logins detected."

        # 5. Warning (Fair) Checks
        if cpu >= settings.cpu_warning_threshold:
            return "Fair", f"Elevated CPU utilization: {cpu:.1f}% exceeds warning baseline."
        if ram >= settings.ram_warning_threshold:
            return "Fair", f"Elevated memory usage: {ram:.1f}% exceeds warning baseline."
        if latency >= settings.latency_warning_ms:
            return "Fair", f"Elevated latency: {latency:.1f}ms."
        if loss >= settings.packet_loss_warning_percent:
            return "Fair", f"Moderate packet loss: {loss:.1f}%."

        # 6. Good (Normal minor variance) Checks
        if cpu > 50.0 or ram > 65.0 or latency > 40.0:
            return "Good", "Normal operational state with moderate workload."

        # 7. Excellent (Healthy nominal)
        return "Excellent", "Nominal baselines: All telemetry signals optimal."
