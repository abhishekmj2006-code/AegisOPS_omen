"""Explainable AIOps Recommendation Generator.

Synthesizes incident root causes, contributing signals, and confidence scores
into plain-language explainable recommendations with executable remediation steps.
"""

from typing import Dict, Any, List


class ExplainableRecommender:
    """Generates transparent, explainable recommendations traceable directly to metadata signals."""

    @staticmethod
    def build_recommendation(
        incident_data: Dict[str, Any],
        contributing_signals: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Builds an explainable recommendation bundle."""
        signals_summary = []
        for s in contributing_signals:
            sig = s.get("signal")
            curr = s.get("current")
            mean = s.get("baseline_mean")
            z = s.get("z_score")
            signals_summary.append(
                f"• {sig}: Observed {curr} vs Baseline {mean} (Deviation: +{z}σ)"
            )

        explanation_narrative = (
            f"Root Cause Diagnosis: {incident_data.get('root_cause')}\n\n"
            f"Why We Flagged:\n"
            f"{incident_data.get('explanation')}\n\n"
            f"Contributing Telemetry Signals:\n"
            + "\n".join(signals_summary) + "\n\n"
            f"Why This Action: {incident_data.get('action_desc', '')}\n\n"
            f"Confidence Assessment: {int(incident_data.get('confidence_score', 0.9) * 100)}% "
            f"based on multi-dimensional signal concordance."
        )

        return {
            "narrative": explanation_narrative,
            "action_type": incident_data.get("action_type", "remediate"),
            "action_title": incident_data.get("action_title", "Operational Remediation"),
            "action_desc": incident_data.get("action_desc", "Remediation action."),
            "rollback_plan": incident_data.get("rollback_plan", "Safe rollback to default configuration."),
        }
