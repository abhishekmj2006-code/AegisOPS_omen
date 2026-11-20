import re
import uuid
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from models.metric import SystemMetrics

UUID_REGEX = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class OutgoingPayload(BaseModel):
    """Standardized outgoing message format transmitted to the central backend."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    message_id: str = Field(..., description="Unique UUID v4 message identifier")
    tenant_id: str = Field(..., min_length=1, max_length=64, description="Tenant identifier")
    device_id: str = Field(..., min_length=1, max_length=64, description="Device identifier")
    timestamp: str = Field(..., description="UTC ISO 8601 formatted timestamp")
    region: str = Field(default="ap-south-1", min_length=1, max_length=32, description="Deployment region")
    source_timezone: str = Field(default="UTC", description="Local timezone identifier")
    metrics: SystemMetrics = Field(..., description="Sanitized and validated system metrics")
    collector_status: Literal["online", "degraded", "recovering", "offline"] = Field(
        default="online", description="Health status of the collector"
    )

    @field_validator("message_id")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        if not UUID_REGEX.match(v):
            raise ValueError(f"message_id '{v}' is not a valid UUID format")
        return v

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        if not (v.endswith("Z") or "+00:00" in v):
            raise ValueError("timestamp must be a UTC ISO 8601 string with 'Z' suffix")
        return v
