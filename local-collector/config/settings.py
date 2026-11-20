"""Application settings and configuration management."""

from dataclasses import dataclass, field
import datetime
import os
from pathlib import Path
import socket
from typing import Optional
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv()


def get_system_timezone() -> str:
    """Detect local system timezone (e.g., Asia/Calcutta or IST), with fallback to UTC."""
    try:
        tz_name = datetime.datetime.now().astimezone().tzname()
        return tz_name or "UTC"
    except Exception:
        return "UTC"


@dataclass
class Settings:
    backend_url: str = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    tenant_id: str = os.getenv("TENANT_ID", "TENANT_001")
    device_id: str = os.getenv("DEVICE_ID", socket.gethostname() or "DEVICE_001")
    region: str = os.getenv("REGION", "ap-south-1")
    collection_interval: float = float(os.getenv("COLLECTION_INTERVAL", "5.0"))
    heartbeat_interval: float = float(os.getenv("HEARTBEAT_INTERVAL", "30.0"))
    network_target: str = os.getenv("NETWORK_TARGET", "8.8.8.8")
    db_path: str = os.getenv("DB_PATH", str(BASE_DIR / "local_collector.db"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    demo_mode: bool = os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")
    collector_api_key: str = os.getenv("COLLECTOR_API_KEY", "aegis_token_sec_9942")
    source_timezone: str = os.getenv("SOURCE_TIMEZONE") or get_system_timezone()
    verify_ssl: bool = os.getenv("VERIFY_SSL", "true").lower() in ("true", "1", "yes")
    app_name: str = "AegisOPS Secure Collector"
    app_version: str = "2.0.0"

    def update(
        self,
        backend_url: Optional[str] = None,
        tenant_id: Optional[str] = None,
        device_id: Optional[str] = None,
        region: Optional[str] = None,
        collection_interval: Optional[float] = None,
        network_target: Optional[str] = None,
    ) -> None:
        """Update settings dynamically and persist to .env."""
        if backend_url is not None:
            self.backend_url = backend_url.rstrip("/")
        if tenant_id is not None:
            self.tenant_id = tenant_id.strip()
        if device_id is not None:
            self.device_id = device_id.strip()
        if region is not None:
            self.region = region.strip()
        if collection_interval is not None:
            self.collection_interval = max(1.0, float(collection_interval))
        if network_target is not None:
            self.network_target = network_target.strip()

        # Save to .env
        env_content = (
            f"BACKEND_URL={self.backend_url}\n"
            f"TENANT_ID={self.tenant_id}\n"
            f"DEVICE_ID={self.device_id}\n"
            f"REGION={self.region}\n"
            f"COLLECTION_INTERVAL={self.collection_interval}\n"
            f"HEARTBEAT_INTERVAL={self.heartbeat_interval}\n"
            f"NETWORK_TARGET={self.network_target}\n"
            f"DB_PATH={self.db_path}\n"
            f"LOG_LEVEL={self.log_level}\n"
            f"DEMO_MODE={str(self.demo_mode).lower()}\n"
        )
        try:
            with open(ENV_FILE, "w", encoding="utf-8") as f:
                f.write(env_content)
        except Exception:
            pass


_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
