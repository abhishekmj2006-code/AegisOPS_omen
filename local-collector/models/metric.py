"""Pydantic model for system metrics."""

from pydantic import BaseModel, ConfigDict, Field


class SystemMetrics(BaseModel):
    """Approved real-time system metrics collected from the local machine.
    
    Strict allowlist: Extra fields are explicitly forbidden.
    """
    model_config = ConfigDict(extra="forbid", frozen=True)

    cpu_usage: float = Field(..., ge=0.0, le=100.0, description="CPU usage percentage")
    ram_usage: float = Field(..., ge=0.0, le=100.0, description="RAM usage percentage")
    ram_total_gb: float = Field(default=0.0, ge=0.0, description="Total physical RAM in GB")
    ram_available_gb: float = Field(default=0.0, ge=0.0, description="Available RAM in GB")
    disk_usage: float = Field(..., ge=0.0, le=100.0, description="Primary disk usage percentage")
    disk_read_mbs: float = Field(default=0.0, ge=0.0, description="Disk read rate in MB/s")
    disk_write_mbs: float = Field(default=0.0, ge=0.0, description="Disk write rate in MB/s")
    network_upload_kbps: float = Field(default=0.0, ge=0.0, description="Network upload rate in KB/s")
    network_download_kbps: float = Field(default=0.0, ge=0.0, description="Network download rate in KB/s")
    network_latency_ms: float = Field(..., ge=0.0, description="Ping/connect latency in milliseconds")
    packet_loss_percent: float = Field(..., ge=0.0, le=100.0, description="Packet loss percentage")
    failed_login_count: int = Field(default=0, ge=0, description="Count of failed login attempts")
    security_threat_level: str = Field(default="nominal", description="Local-first threat level (nominal, elevated, critical)")
