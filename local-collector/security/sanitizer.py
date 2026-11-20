from dataclasses import dataclass, field
import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import ValidationError

from security.allowlist import (
    ALLOWED_METRICS_KEYS,
    ALLOWED_TOP_LEVEL_KEYS,
    SENSITIVE_KEY_NAMES,
)
from models.metric import SystemMetrics
from models.payload import OutgoingPayload
from utils.logger import get_logger

logger = get_logger("Sanitizer")

SECRET_VALUE_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
    re.compile(r"ey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    re.compile(r"(?i)AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)(password|secret|bearer|token)\s*[:=]\s*\S+"),
]


@dataclass
class SanitizationResult:
    """Result summary of a data sanitization pass."""
    sanitized_data: Dict[str, Any]
    sensitive_fields_detected: int = 0
    fields_removed: List[str] = field(default_factory=list)
    status: str = "CLEAN"
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)
    original_input_summary: Dict[str, Any] = field(default_factory=dict)


class Sanitizer:
    """Multi-stage sanitizer: structured allowlisting, secret detection, and schema validation."""

    def __init__(self) -> None:
        pass

    def is_key_sensitive(self, key_name: str) -> bool:
        clean_key = key_name.lower().strip()
        for sensitive in SENSITIVE_KEY_NAMES:
            if sensitive in clean_key:
                return True
        return False

    def value_contains_secret(self, val: Any) -> bool:
        if not isinstance(val, str):
            return False
        for pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(val):
                return True
        return False

    def sanitize_metrics(self, raw_metrics: Dict[str, Any]) -> Tuple[Dict[str, Any], int, List[str]]:
        sanitized: Dict[str, Any] = {}
        sensitive_count = 0
        removed_fields: List[str] = []

        for key, value in raw_metrics.items():
            is_sensitive = self.is_key_sensitive(key)
            has_secret_val = self.value_contains_secret(value)

            if is_sensitive or has_secret_val:
                sensitive_count += 1
                removed_fields.append(f"metrics.{key}")
                logger.warning(f"Sanitizer detected & stripped sensitive field: metrics.{key}")
                continue

            if key not in ALLOWED_METRICS_KEYS:
                removed_fields.append(f"metrics.{key}")
                logger.info(f"Sanitizer stripped unallowlisted field: metrics.{key}")
                continue

            try:
                if key == "failed_login_count":
                    sanitized[key] = int(value)
                elif key == "security_threat_level":
                    sanitized[key] = str(value)
                else:
                    sanitized[key] = round(float(value), 2)
            except (ValueError, TypeError):
                removed_fields.append(f"metrics.{key} (invalid type)")
                logger.warning(f"Sanitizer dropped field due to invalid type: metrics.{key}")

        return sanitized, sensitive_count, removed_fields

    def sanitize_payload(self, raw_payload: Dict[str, Any]) -> SanitizationResult:
        sensitive_detected = 0
        fields_removed: List[str] = []
        cleaned_top_level: Dict[str, Any] = {}

        for key, value in raw_payload.items():
            if self.is_key_sensitive(key) or self.value_contains_secret(value):
                sensitive_detected += 1
                fields_removed.append(key)
                logger.warning(f"Sanitizer stripped sensitive top-level key: {key}")
                continue

            if key not in ALLOWED_TOP_LEVEL_KEYS:
                fields_removed.append(key)
                logger.info(f"Sanitizer stripped unauthorized top-level key: {key}")
                continue

            cleaned_top_level[key] = value

        raw_metrics = cleaned_top_level.get("metrics", {})
        if not isinstance(raw_metrics, dict):
            raw_metrics = {}

        sanitized_metrics, met_sens_count, met_removed = self.sanitize_metrics(raw_metrics)
        sensitive_detected += met_sens_count
        fields_removed.extend(met_removed)
        cleaned_top_level["metrics"] = sanitized_metrics

        is_valid = False
        val_errors: List[str] = []
        try:
            validated = OutgoingPayload(**cleaned_top_level)
            final_data = validated.model_dump()
            is_valid = True
        except ValidationError as e:
            final_data = cleaned_top_level
            for err in e.errors():
                loc = ".".join(str(x) for x in err["loc"])
                val_errors.append(f"{loc}: {err['msg']}")
            logger.error(f"Payload validation failed: {val_errors}")

        if not is_valid:
            status = "REJECTED"
        elif sensitive_detected > 0 or len(fields_removed) > 0:
            status = "SANITIZED"
        else:
            status = "CLEAN"

        return SanitizationResult(
            sanitized_data=final_data,
            sensitive_fields_detected=sensitive_detected,
            fields_removed=fields_removed,
            status=status,
            is_valid=is_valid,
            validation_errors=val_errors,
            original_input_summary={
                "top_level_keys": list(raw_payload.keys()),
                "metrics_keys": list(raw_metrics.keys()) if isinstance(raw_metrics, dict) else [],
            },
        )
