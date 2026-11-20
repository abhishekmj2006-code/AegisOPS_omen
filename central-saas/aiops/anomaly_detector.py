"""Dynamic Anomaly Detection Engine.

Goes beyond static thresholds using rolling baselines (mean & standard deviation)
and Z-score statistical divergence to identify unexpected metric deviations.
"""

import math
from typing import Dict, List, Tuple, Any
from storage.models import TelemetryRecord
from saas_config.settings import settings


class AnomalyDetector:
    """Calculates statistical rolling baselines and flags anomalous multi-dimensional telemetry."""

    @staticmethod
    def evaluate(
        current_metrics: Dict[str, Any],
        history: List[TelemetryRecord],
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """Analyzes current metrics against historical baseline.
        
        Returns:
            (is_anomaly, contributing_signals)
        """
        contributing: List[Dict[str, Any]] = []

        if len(history) < 3:
            # Not enough historical baseline yet, use heuristic threshold checks
            cpu = float(current_metrics.get("cpu_usage", 0.0))
            lat = float(current_metrics.get("network_latency_ms", 0.0))
            loss = float(current_metrics.get("packet_loss_percent", 0.0))
            logins = int(current_metrics.get("failed_login_count", 0))

            if cpu > settings.cpu_warning_threshold:
                contributing.append({
                    "signal": "cpu_usage",
                    "current": cpu,
                    "baseline_mean": 20.0,
                    "z_score": 2.5,
                    "severity": "high" if cpu > settings.cpu_critical_threshold else "medium",
                })
            if lat > settings.latency_warning_ms:
                contributing.append({
                    "signal": "network_latency_ms",
                    "current": lat,
                    "baseline_mean": 25.0,
                    "z_score": 2.8,
                    "severity": "high" if lat > settings.latency_critical_ms else "medium",
                })
            if loss > settings.packet_loss_warning_percent:
                contributing.append({
                    "signal": "packet_loss_percent",
                    "current": loss,
                    "baseline_mean": 0.0,
                    "z_score": 3.0,
                    "severity": "high",
                })
            if logins >= settings.failed_logins_incident_threshold:
                contributing.append({
                    "signal": "failed_login_count",
                    "current": logins,
                    "baseline_mean": 0.0,
                    "z_score": 4.0,
                    "severity": "critical",
                })

            return (len(contributing) > 0), contributing

        # Calculate rolling baseline for each key metric
        # Sensible minimum operational floors prevent normal low-usage idle fluctuations (e.g. 5% -> 18% CPU) from triggering false alarms
        min_operational_floors = {
            "cpu_usage": 60.0,             # Do not flag CPU anomalies if CPU is below 60%
            "ram_usage": 75.0,             # Do not flag RAM anomalies if RAM is below 75%
            "network_latency_ms": 60.0,    # Do not flag latency anomalies if latency is below 60ms
            "packet_loss_percent": 2.0,    # Do not flag loss anomalies if packet loss is below 2%
        }

        signals_to_check = [
            ("cpu_usage", float(current_metrics.get("cpu_usage", 0.0)), settings.cpu_warning_threshold),
            ("ram_usage", float(current_metrics.get("ram_usage", 0.0)), settings.ram_warning_threshold),
            ("network_latency_ms", float(current_metrics.get("network_latency_ms", 0.0)), settings.latency_warning_ms),
            ("packet_loss_percent", float(current_metrics.get("packet_loss_percent", 0.0)), settings.packet_loss_warning_percent),
        ]

        for sig_name, curr_val, warn_threshold in signals_to_check:
            # Operational Floor Check: Ignore fluctuations below the minimum operational threshold
            min_floor = min_operational_floors.get(sig_name, 0.0)
            if curr_val < min_floor and curr_val < warn_threshold:
                continue

            vals = [getattr(r, sig_name) for r in history if hasattr(r, sig_name)]
            if not vals:
                continue

            mean = sum(vals) / len(vals)
            variance = sum((x - mean) ** 2 for x in vals) / len(vals)
            std_dev = math.sqrt(variance) if variance > 0.001 else 1.0

            z_score = (curr_val - mean) / std_dev

            # Anomaly triggered if statistical Z-score exceeds threshold AND value breaches operational floor, OR breached absolute safety boundary
            if (z_score >= settings.anomaly_z_score_threshold and curr_val >= min_floor and curr_val > mean * 1.25) or curr_val >= warn_threshold:
                severity = "critical" if z_score >= 3.5 or curr_val >= warn_threshold * 1.3 else "high"
                contributing.append({
                    "signal": sig_name,
                    "current": round(curr_val, 2),
                    "baseline_mean": round(mean, 2),
                    "baseline_std": round(std_dev, 2),
                    "z_score": round(z_score, 2),
                    "severity": severity,
                })

        # Explicit check for security authentication bursts
        failed_logins = int(current_metrics.get("failed_login_count", 0))
        if failed_logins >= settings.failed_logins_incident_threshold:
            contributing.append({
                "signal": "failed_login_count",
                "current": failed_logins,
                "baseline_mean": 0.0,
                "z_score": 5.0,
                "severity": "critical",
            })

        return (len(contributing) > 0), contributing
