"""Central SaaS Platform Configuration."""

import os
from typing import List
from pydantic import BaseModel


class CentralSettings(BaseModel):
    app_name: str = "AegisOPS Central SaaS Platform"
    app_version: str = "2.0.0"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # Storage
    database_url: str = os.getenv("SAAS_DATABASE_URL", "sqlite:///./central_saas.db")
    
    # Supported deployment regions
    allowed_regions: List[str] = ["ap-south-1", "us-east-1", "eu-central-1", "eu-west-1", "us-west-2"]
    default_region: str = "ap-south-1"

    # Authentication & Security
    require_collector_auth: bool = True
    valid_collector_tokens: List[str] = ["aegis_token_sec_9942", "aegis_demo_token_123"]
    
    # Fleet Heartbeat & Health Thresholds
    heartbeat_timeout_seconds: float = 60.0  # Downgrades to Poor if no heartbeat within 60s
    stale_data_seconds: float = 30.0         # Downgrades to Fair if no metric data within 30s
    
    # AIOps Baseline & Anomaly Thresholds
    baseline_window_samples: int = 15        # Number of samples to compute rolling mean & std
    anomaly_z_score_threshold: float = 2.0   # Standard deviations above mean to flag anomaly
    
    # Static fallback bounds
    cpu_warning_threshold: float = 75.0
    cpu_critical_threshold: float = 90.0
    ram_warning_threshold: float = 80.0
    ram_critical_threshold: float = 92.0
    latency_warning_ms: float = 80.0
    latency_critical_ms: float = 150.0
    packet_loss_warning_percent: float = 2.0
    packet_loss_critical_percent: float = 5.0
    failed_logins_incident_threshold: int = 3


settings = CentralSettings()
