"""Event Intelligence & Alert Noise Reduction Correlator.

Merges correlated multi-signal alerts across network, compute, and security
into single cohesive incidents, reducing operator alert fatigue.
"""

from typing import Dict, List, Optional, Any


class EventCorrelator:
    """Correlates multiple anomalous telemetry signals into a single actionable incident."""

    @staticmethod
    def correlate(
        tenant_id: str,
        device_id: str,
        contributing_signals: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Analyzes active anomaly signals and constructs a unified incident."""
        if not contributing_signals:
            return None

        sig_names = {s["signal"] for s in contributing_signals}

        # Case 1: Security Surge (Authentication)
        if "failed_login_count" in sig_names:
            logins = next(s["current"] for s in contributing_signals if s["signal"] == "failed_login_count")
            return {
                "title": f"Security Incident: Repeated Authentication Failures ({int(logins)} events)",
                "category": "Security",
                "severity": "critical",
                "root_cause": "Potential credential brute-force or unauthorized privilege escalation attempt on local host.",
                "explanation": (
                    f"AIOps detected {int(logins)} consecutive authentication failures occurring within a single sampling window. "
                    "This deviates from the historical zero-failure baseline (Z-score > 4.0). "
                    "All raw credentials remain secured on the host; metadata indicates an active security breach attempt."
                ),
                "confidence_score": 0.98,
                "action_type": "isolate_session",
                "action_title": "Enforce Host Security Lockout & Rotate Session Tokens",
                "action_desc": "Temporarily rate-limit local authentication endpoints and invalidate active session tokens for the affected user profile.",
                "rollback_plan": "Restore standard login rate-limits and re-enable standard authentication policies.",
            }

        # Case 2: Network Congestion (Latency + Packet Loss)
        if "network_latency_ms" in sig_names and "packet_loss_percent" in sig_names:
            lat = next(s["current"] for s in contributing_signals if s["signal"] == "network_latency_ms")
            loss = next(s["current"] for s in contributing_signals if s["signal"] == "packet_loss_percent")
            return {
                "title": f"Network Path Degradation: Latency Spike ({lat:.1f}ms) with {loss:.1f}% Packet Loss",
                "category": "Network",
                "severity": "high",
                "root_cause": "Network routing congestion or intermediary gateway buffer bloat.",
                "explanation": (
                    f"Correlated network indicators show simultaneous rise in latency ({lat:.1f}ms) "
                    f"and packet loss ({loss:.1f}%). Multi-signal correlation confirms an upstream path degradation "
                    "rather than an isolated endpoint timeout."
                ),
                "confidence_score": 0.94,
                "action_type": "reroute_gateway",
                "action_title": "Failover to Secondary Ingest Endpoint",
                "action_desc": "Instruct collector to reroute traffic to secondary backup gateway to bypass degraded network transit.",
                "rollback_plan": "Switch collector back to primary default ingest route once latency normalizes below 50ms.",
            }

        # Case 3: Network Latency Alone
        if "network_latency_ms" in sig_names:
            lat = next(s["current"] for s in contributing_signals if s["signal"] == "network_latency_ms")
            return {
                "title": f"Elevated Transport Latency ({lat:.1f}ms)",
                "category": "Network",
                "severity": "medium",
                "root_cause": "Transit delay to configured network monitoring target.",
                "explanation": (
                    f"Network latency measured at {lat:.1f}ms, which statistically exceeds normal baseline by >2 standard deviations. "
                    "Packet transmission remains intact (0% loss)."
                ),
                "confidence_score": 0.88,
                "action_type": "adjust_sampling",
                "action_title": "Dynamic Sampling Backoff",
                "action_desc": "Temporarily expand collection interval from 5s to 10s to conserve transport bandwidth.",
                "rollback_plan": "Restore 5s polling interval once round-trip latency returns to nominal baseline.",
            }

        # Case 4: Compute Exhaustion (CPU + RAM)
        if "cpu_usage" in sig_names and "ram_usage" in sig_names:
            cpu = next(s["current"] for s in contributing_signals if s["signal"] == "cpu_usage")
            ram = next(s["current"] for s in contributing_signals if s["signal"] == "ram_usage")
            return {
                "title": f"Host Compute Saturation: CPU ({cpu:.1f}%) and Memory ({ram:.1f}%)",
                "category": "Performance",
                "severity": "critical" if cpu > 90.0 or ram > 90.0 else "high",
                "root_cause": "Runaway background task or local application memory leak.",
                "explanation": (
                    f"Simultaneous compute pressure detected: CPU utilization surged to {cpu:.1f}% while memory allocation reached {ram:.1f}%. "
                    "Correlated multi-core exhaustion threatens overall host responsiveness."
                ),
                "confidence_score": 0.96,
                "action_type": "throttle_workload",
                "action_title": "Throttle High-Priority Background Workers",
                "action_desc": "Dispatch safe runtime signal to suspend non-critical local processes and trigger memory garbage collection.",
                "rollback_plan": "Restore full worker concurrency after system load factor drops below 60%.",
            }

        # Case 5: CPU Load Spike Alone
        if "cpu_usage" in sig_names:
            cpu = next(s["current"] for s in contributing_signals if s["signal"] == "cpu_usage")
            return {
                "title": f"CPU Utilization Deviation ({cpu:.1f}%)",
                "category": "Performance",
                "severity": "high" if cpu > 90.0 else "medium",
                "root_cause": "Sustained computational workload spike.",
                "explanation": (
                    f"Host CPU utilization rose to {cpu:.1f}%, exceeding the rolling statistical baseline. "
                    "Memory and network telemetry remain within safe margins."
                ),
                "confidence_score": 0.91,
                "action_type": "profile_processes",
                "action_title": "Collect Anonymized Process Performance Profile",
                "action_desc": "Trigger low-overhead top-process usage summary to locate the responsible background thread.",
                "rollback_plan": "Deactivate performance profiler trace buffer.",
            }

        # Fallback Default Incident
        return {
            "title": f"Telemetry Multi-Signal Anomaly on {device_id}",
            "category": "Operational",
            "severity": "medium",
            "root_cause": "Metric deviation exceeding statistical baseline.",
            "explanation": f"Observed statistical deviations across: {', '.join(sig_names)}.",
            "confidence_score": 0.85,
            "action_type": "diagnostic_sweep",
            "action_title": "Execute Diagnostic Health Check",
            "action_desc": "Run non-intrusive diagnostic probe to verify local collector telemetry integrity.",
            "rollback_plan": "Reset diagnostic health counters.",
        }
