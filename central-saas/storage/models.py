"""Central SaaS Database Models using SQLAlchemy."""

from datetime import datetime, timezone
from typing import Any, Dict, List
import uuid
import json

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Tenant(Base):
    """Multi-tenant account boundary with data residency region."""
    __tablename__ = "tenants"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    region = Column(String(64), nullable=False, default="ap-south-1")
    created_at = Column(DateTime, default=utc_now)

    collectors = relationship("CollectorNode", back_populates="tenant", cascade="all, delete-orphan")
    telemetry = relationship("TelemetryRecord", back_populates="tenant", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="tenant", cascade="all, delete-orphan")


class CollectorNode(Base):
    """Registered local collector node in the fleet."""
    __tablename__ = "collector_nodes"

    device_id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), ForeignKey("tenants.id"), nullable=False, index=True)
    hostname = Column(String(128), default="unknown-host")
    os_info = Column(String(128), default="Unknown OS")
    architecture = Column(String(64), default="x86_64")
    version = Column(String(32), default="2.0.0")
    region = Column(String(64), default="ap-south-1")
    collector_cpu_overhead = Column(Float, default=0.2)
    collector_ram_overhead = Column(Float, default=24.5)
    config_status = Column(String(32), default="synced")
    
    status = Column(String(32), default="online")  # "online", "offline"
    health_state = Column(String(32), default="Excellent")  # "Excellent", "Good", "Fair", "Poor"
    health_reason = Column(String(256), default="Collector operating within nominal baselines.")
    
    last_heartbeat = Column(DateTime, default=utc_now)
    last_metric_received = Column(DateTime, default=utc_now)
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="collectors")
    telemetry = relationship("TelemetryRecord", back_populates="collector", cascade="all, delete-orphan")


class TelemetryRecord(Base):
    """Metadata-only metric sample ingested from collector.
    
    Message ID enforces idempotency (duplicate UUIDs rejected).
    """
    __tablename__ = "telemetry_records"

    message_id = Column(String(64), primary_key=True)  # UUID
    tenant_id = Column(String(64), ForeignKey("tenants.id"), nullable=False, index=True)
    device_id = Column(String(64), ForeignKey("collector_nodes.device_id"), nullable=False, index=True)
    
    event_time = Column(DateTime, nullable=False, index=True)  # Event timestamp from payload (UTC)
    received_at = Column(DateTime, default=utc_now, index=True)  # Ingest arrival time (UTC)
    region = Column(String(64), default="ap-south-1")
    source_timezone = Column(String(32), default="UTC")
    
    # Approved Numeric Metrics
    cpu_usage = Column(Float, default=0.0)
    ram_usage = Column(Float, default=0.0)
    disk_usage = Column(Float, default=0.0)
    network_latency_ms = Column(Float, default=0.0)
    packet_loss_percent = Column(Float, default=0.0)
    failed_login_count = Column(Integer, default=0)
    
    # Additional allow-listed metrics
    raw_metrics_json = Column(Text, default="{}")
    collector_status = Column(String(32), default="online")
    
    # Anomaly marker
    is_anomaly = Column(Boolean, default=False)
    anomaly_signals = Column(Text, default="[]")

    tenant = relationship("Tenant", back_populates="telemetry")
    collector = relationship("CollectorNode", back_populates="telemetry")

    def get_metrics_dict(self) -> Dict[str, Any]:
        try:
            return json.loads(self.raw_metrics_json)
        except Exception:
            return {}


class Alert(Base):
    """Atomic metric or security threshold alert."""
    __tablename__ = "alerts"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), ForeignKey("tenants.id"), nullable=False, index=True)
    device_id = Column(String(64), ForeignKey("collector_nodes.device_id"), nullable=False, index=True)
    
    signal_name = Column(String(64), nullable=False)  # "cpu_usage", "latency", "failed_login"
    severity = Column(String(32), default="medium")   # "info", "warning", "high", "critical"
    current_value = Column(Float, default=0.0)
    threshold_value = Column(Float, default=0.0)
    message = Column(String(256), nullable=False)
    
    timestamp = Column(DateTime, default=utc_now, index=True)
    status = Column(String(32), default="active")  # "active", "correlated", "resolved"
    incident_id = Column(String(64), ForeignKey("incidents.id"), nullable=True, index=True)

    incident = relationship("Incident", back_populates="alerts")


class Incident(Base):
    """Correlated multi-signal operational incident."""
    __tablename__ = "incidents"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), ForeignKey("tenants.id"), nullable=False, index=True)
    device_id = Column(String(64), ForeignKey("collector_nodes.device_id"), nullable=False, index=True)
    
    title = Column(String(160), nullable=False)
    category = Column(String(64), nullable=False)  # "Performance", "Network", "Security", "Availability"
    severity = Column(String(32), default="high")  # "low", "medium", "high", "critical"
    status = Column(String(32), default="open")     # "open", "mitigating", "resolved"
    
    root_cause = Column(String(256), nullable=False)
    explanation = Column(Text, nullable=False)
    confidence_score = Column(Float, default=0.90)  # e.g., 0.94 (94%)
    ai_engine = Column(String(64), default="Deterministic AIOps Engine")
    contributing_signals_json = Column(Text, default="[]")
    
    created_at = Column(DateTime, default=utc_now, index=True)
    updated_at = Column(DateTime, default=utc_now)
    last_seen_at = Column(DateTime, default=utc_now)
    occurrence_count = Column(Integer, default=1)

    tenant = relationship("Tenant", back_populates="incidents")
    alerts = relationship("Alert", back_populates="incident")
    remediations = relationship("RemediationAction", back_populates="incident", cascade="all, delete-orphan")

    def get_contributing_signals(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self.contributing_signals_json)
        except Exception:
            return []


class RemediationAction(Base):
    """Autonomous Ops action proposal, review, simulation, execution and rollback trail."""
    __tablename__ = "remediation_actions"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(64), ForeignKey("incidents.id"), nullable=False, index=True)
    tenant_id = Column(String(64), ForeignKey("tenants.id"), nullable=False, index=True)
    
    action_type = Column(String(64), nullable=False)  # "restart_service", "throttle_rate", "flush_cache", "block_ip"
    title = Column(String(160), nullable=False)
    description = Column(Text, nullable=False)
    
    status = Column(String(32), default="pending_approval")  # "pending_approval", "approved", "simulated", "executed", "rolled_back", "rejected"
    policy_check = Column(String(64), default="PASSED (Within autonomous safety guardrails)")
    
    rollback_plan = Column(Text, nullable=False)
    audit_trail_json = Column(Text, default="[]")
    
    operator = Column(String(64), default="Human-in-the-Loop Operator")
    created_at = Column(DateTime, default=utc_now, index=True)
    executed_at = Column(DateTime, nullable=True)

    incident = relationship("Incident", back_populates="remediations")

    def add_audit_entry(self, action: str, details: str, operator: str = "Operator") -> None:
        try:
            entries = json.loads(self.audit_trail_json)
        except Exception:
            entries = []
        entries.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "details": details,
            "operator": operator,
        })
        self.audit_trail_json = json.dumps(entries)


class HealthStateTransition(Base):
    """Auditable log of collector health state changes."""
    __tablename__ = "health_transitions"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), ForeignKey("tenants.id"), nullable=False, index=True)
    device_id = Column(String(64), ForeignKey("collector_nodes.device_id"), nullable=False, index=True)
    previous_state = Column(String(32), nullable=False)
    new_state = Column(String(32), nullable=False)
    reason = Column(String(256), nullable=False)
    timestamp = Column(DateTime, default=utc_now, index=True)

    @property
    def transition_time(self):
        return self.timestamp

    @property
    def old_state(self):
        return self.previous_state

    @property
    def formatted_time(self) -> str:
        return self.timestamp.strftime("%I:%M:%S %p") if self.timestamp else ""


class DeliveryStat(Base):
    """Tracks delivery reliability, SLA latency, and duplicate counts."""
    __tablename__ = "delivery_stats"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    total_received = Column(Integer, default=0)
    total_duplicates = Column(Integer, default=0)
    updated_at = Column(DateTime, default=utc_now)
