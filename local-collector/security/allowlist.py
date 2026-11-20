"""Strict allowlists and sensitivity rules for data transmission."""

from typing import FrozenSet

# Strict top-level keys permitted in outgoing payloads
ALLOWED_TOP_LEVEL_KEYS: FrozenSet[str] = frozenset({
    "message_id",
    "tenant_id",
    "device_id",
    "timestamp",
    "region",
    "source_timezone",
    "metrics",
    "collector_status",
})

# Strict metrics keys permitted in metrics dictionary
ALLOWED_METRICS_KEYS: FrozenSet[str] = frozenset({
    "cpu_usage",
    "ram_usage",
    "ram_total_gb",
    "ram_available_gb",
    "disk_usage",
    "disk_read_mbs",
    "disk_write_mbs",
    "network_upload_kbps",
    "network_download_kbps",
    "network_latency_ms",
    "packet_loss_percent",
    "failed_login_count",
    "security_threat_level",
})

# Blocklisted sensitive field names (case-insensitive substring match)
SENSITIVE_KEY_NAMES: FrozenSet[str] = frozenset({
    "password",
    "passwd",
    "pwd",
    "secret",
    "api_key",
    "apikey",
    "token",
    "access_token",
    "auth_token",
    "bearer",
    "cookie",
    "session",
    "private_key",
    "privatekey",
    "ssh_key",
    "credential",
    "credentials",
    "auth",
    "authorization",
    "ssn",
    "credit_card",
    "pin",
    "cvv",
    "raw_log",
    "cmdline",
    "command_line",
    "email",
    "phone",
})

# Permitted collector status values
ALLOWED_COLLECTOR_STATUSES: FrozenSet[str] = frozenset({
    "online",
    "degraded",
    "recovering",
    "offline",
})
