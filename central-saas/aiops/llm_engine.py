"""Google GenAI LLM Copilot Engine for AegisOPS.

Integrates the official google-genai SDK using Google Gemini models (gemini-2.5-flash)
for autonomous root cause analysis and explainable remediation recommendations.
Provides seamless zero-error fallback to the local deterministic statistical engine
when GEMINI_API_KEY is not configured or in offline environments.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

from aiops.correlator import EventCorrelator
from aiops.recommender import ExplainableRecommender

logger = logging.getLogger("aegisops.aiops.llm")

# Model configuration
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


def get_gemini_api_key() -> Optional[str]:
    """Retrieve GEMINI_API_KEY from environment or local .env configuration."""
    # 1. Environment variables
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if key and key.strip():
        return key.strip()

    # 2. Check known .env locations
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidate_paths = [
        os.path.join(base_dir, "..", ".env"),
        os.path.join(base_dir, "..", "..", ".env"),
        os.path.join(base_dir, "..", "..", "local-collector", ".env"),
    ]
    for env_path in candidate_paths:
        if os.path.isfile(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GEMINI_API_KEY=") or line.startswith("GOOGLE_API_KEY="):
                            parts = line.split("=", 1)
                            val = parts[1].strip().strip('"').strip("'")
                            if val:
                                return val
            except Exception:
                pass
    return None


class AIOpsLLMEngine:
    """AIOps Copilot Engine combining Google Gemini generative intelligence with local heuristic resilience."""

    @classmethod
    def is_gemini_active(cls) -> bool:
        """Check whether Google GenAI is configured with a valid API key."""
        return bool(get_gemini_api_key())

    @classmethod
    def analyze(
        cls,
        tenant_id: str,
        device_id: str,
        current_metrics: Dict[str, Any],
        contributing_signals: List[Dict[str, Any]],
        collector_metadata: Optional[Dict[str, Any]] = None,
        model_name: str = DEFAULT_GEMINI_MODEL,
    ) -> Optional[Dict[str, Any]]:
        """Analyzes anomaly telemetry signals using Google Gemini or seamless local fallback."""
        if not contributing_signals:
            return None

        api_key = get_gemini_api_key()
        if api_key:
            try:
                result = cls._call_gemini_api(
                    api_key=api_key,
                    tenant_id=tenant_id,
                    device_id=device_id,
                    current_metrics=current_metrics,
                    contributing_signals=contributing_signals,
                    collector_metadata=collector_metadata or {},
                    model_name=model_name,
                )
                if result:
                    return result
            except Exception as e:
                logger.warning(
                    f"Gemini AI reasoning call encountered error or timeout ({type(e).__name__}: {e}). "
                    "Engaging deterministic statistical fallback engine."
                )

        # Seamless local deterministic fallback
        return cls._local_statistical_fallback(
            tenant_id=tenant_id,
            device_id=device_id,
            current_metrics=current_metrics,
            contributing_signals=contributing_signals,
        )

    @classmethod
    def _call_gemini_api(
        cls,
        api_key: str,
        tenant_id: str,
        device_id: str,
        current_metrics: Dict[str, Any],
        contributing_signals: List[Dict[str, Any]],
        collector_metadata: Dict[str, Any],
        model_name: str,
    ) -> Optional[Dict[str, Any]]:
        """Invokes official google-genai SDK with strict JSON schema."""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        # System instruction as required
        system_instruction = (
            "You are an autonomous AIOps Root Cause Analysis Engine for AegisOPS enterprise observability. "
            "Analyze the provided allow-listed infrastructure metadata, diagnose the exact root cause, "
            "assign a confidence score (0-100%), explain which signals contributed, and recommend a safe, "
            "policy-compliant remediation action."
        )

        # Build sanitized allow-listed payload (zero secrets, zero passwords, zero raw command line args)
        telemetry_payload = {
            "tenant_id": tenant_id,
            "device_id": device_id,
            "collector_metadata": {
                "region": collector_metadata.get("region", "ap-south-1"),
                "health_state": collector_metadata.get("health_state", "Good"),
                "collector_version": collector_metadata.get("collector_version", "2.0.0"),
            },
            "metrics_summary": {
                "cpu_usage_percent": current_metrics.get("cpu_usage"),
                "ram_usage_percent": current_metrics.get("ram_usage"),
                "disk_usage_percent": current_metrics.get("disk_usage"),
                "network_latency_ms": current_metrics.get("network_latency_ms"),
                "packet_loss_percent": current_metrics.get("packet_loss_percent"),
                "failed_login_count": current_metrics.get("failed_login_count", 0),
            },
            "anomaly_signals": [
                {
                    "signal": s.get("signal"),
                    "observed": s.get("current"),
                    "baseline_mean": s.get("baseline_mean"),
                    "z_score": s.get("z_score"),
                    "severity": s.get("severity", "medium"),
                }
                for s in contributing_signals
            ],
            "schema_contract": {
                "root_cause": "Brief technical root-cause title",
                "why_flagged": "Explanation of the anomaly pattern and why baseline was breached",
                "contributing_signals": ["Signal 1 with delta", "Signal 2 with delta"],
                "confidence_score": 92,
                "recommended_action": "Safe suggested remediation command/action",
                "why_this_action": "Explanation of why this specific fix mitigates the root cause safely",
                "ai_engine": f"Google Gemini ({model_name})",
            },
        }

        prompt = (
            "Analyze this sanitized telemetry metadata and return a JSON object adhering strictly "
            f"to the schema contract:\n\n{json.dumps(telemetry_payload, indent=2)}"
        )

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            temperature=0.2,
        )

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config,
        )

        raw_text = response.text or "{}"
        parsed = json.loads(raw_text)

        # Normalize confidence score to 0.0 - 1.0 float
        conf = parsed.get("confidence_score", 90)
        if isinstance(conf, (int, float)):
            conf_norm = conf / 100.0 if conf > 1.0 else float(conf)
        else:
            conf_norm = 0.90

        # Infer category and severity based on signals
        sig_names = {s.get("signal") for s in contributing_signals}
        if "failed_login_count" in sig_names:
            category = "Security"
            severity = "critical"
        elif "network_latency_ms" in sig_names or "packet_loss_percent" in sig_names:
            category = "Network"
            severity = "high" if current_metrics.get("network_latency_ms", 0) > 100 else "medium"
        elif "cpu_usage" in sig_names or "ram_usage" in sig_names:
            category = "Performance"
            severity = "critical" if current_metrics.get("cpu_usage", 0) > 90 or current_metrics.get("ram_usage", 0) > 90 else "high"
        else:
            category = "Operational"
            severity = "medium"

        root_cause = parsed.get("root_cause", "Anomaly pattern identified by Google Gemini")
        why_flagged = parsed.get("why_flagged", "Statistical threshold breach detected.")
        contrib_lines = parsed.get("contributing_signals", [])
        if isinstance(contrib_lines, list):
            contrib_text = "\n".join(f"• {c}" for c in contrib_lines)
        else:
            contrib_text = str(contrib_lines)

        recommended_action = parsed.get("recommended_action", "Operational Remediation")
        why_this_action = parsed.get("why_this_action", "Mitigate resource saturation and restore nominal baseline.")
        ai_engine_name = parsed.get("ai_engine", f"Google Gemini ({model_name})")

        # Clean structured narrative
        narrative = (
            f"Root Cause Diagnosis: {root_cause}\n\n"
            f"Why We Flagged:\n{why_flagged}\n\n"
            f"Contributing Telemetry Signals:\n{contrib_text}\n\n"
            f"Why This Action: {why_this_action}\n\n"
            f"Confidence Assessment: {int(conf_norm * 100)}% based on Google GenAI multi-dimensional inference.\n\n"
            f"AI Engine: {ai_engine_name}"
        )

        return {
            "title": f"{root_cause} on {device_id}",
            "category": category,
            "severity": severity,
            "root_cause": root_cause,
            "explanation": narrative,
            "confidence_score": conf_norm,
            "contributing_signals": contributing_signals,
            "action_type": "gemini_copilot_remediation",
            "action_title": recommended_action,
            "action_desc": why_this_action,
            "rollback_plan": "Revert configuration to preceding nominal telemetry baseline.",
            "ai_engine": ai_engine_name,
        }

    @classmethod
    def _local_statistical_fallback(
        cls,
        tenant_id: str,
        device_id: str,
        current_metrics: Dict[str, Any],
        contributing_signals: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Deterministic statistical fallback ensuring 100% reliability offline."""
        incident_data = EventCorrelator.correlate(tenant_id, device_id, contributing_signals)
        if not incident_data:
            return None

        rec_bundle = ExplainableRecommender.build_recommendation(incident_data, contributing_signals)
        ai_engine_name = "Deterministic AIOps Statistical Engine (Local Fallback)"

        # Append engine confirmation to narrative
        narrative = rec_bundle["narrative"] + f"\n\nAI Engine: {ai_engine_name}"

        return {
            "title": incident_data["title"],
            "category": incident_data["category"],
            "severity": incident_data["severity"],
            "root_cause": incident_data["root_cause"],
            "explanation": narrative,
            "confidence_score": incident_data["confidence_score"],
            "contributing_signals": contributing_signals,
            "action_type": rec_bundle["action_type"],
            "action_title": rec_bundle["action_title"],
            "action_desc": rec_bundle["action_desc"],
            "rollback_plan": rec_bundle["rollback_plan"],
            "ai_engine": ai_engine_name,
        }
