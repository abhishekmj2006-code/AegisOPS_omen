import json
import platform
import socket
from typing import Any, Dict, Optional, Tuple
import httpx

from config.settings import Settings
from utils.logger import get_logger

logger = get_logger("APIClient")


class APIClient:
    """FastAPI-compatible HTTP client using httpx with robust error handling and transport support."""

    def __init__(
        self,
        settings: Settings,
        timeout: float = 5.0,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.settings = settings
        self.timeout = timeout
        self.transport = transport

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"{self.settings.app_name}/{self.settings.app_version}",
            "X-Tenant-ID": self.settings.tenant_id,
            "X-Device-ID": self.settings.device_id,
            "X-Source-Timezone": getattr(self.settings, "source_timezone", "UTC"),
            "X-Hostname": socket.gethostname() or "aegis-host",
            "X-OS-Info": f"{platform.system()} {platform.release()}",
            "X-Architecture": platform.machine() or "x86_64",
            "X-Collector-Version": getattr(self.settings, "app_version", "2.0.0"),
        }
        api_key = getattr(self.settings, "collector_api_key", None)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def check_health(self) -> Tuple[bool, int, str]:
        url = f"{self.settings.backend_url}/api/v1/health"
        try:
            verify_ssl = getattr(self.settings, "verify_ssl", True)
            with httpx.Client(timeout=self.timeout, transport=self.transport, verify=verify_ssl) as client:
                res = client.get(url, headers=self._get_headers())
                if res.is_success:
                    return True, res.status_code, res.text
                return False, res.status_code, res.text
        except httpx.ConnectError:
            return False, 0, "Connection refused (backend unreachable)"
        except httpx.TimeoutException:
            return False, 0, "Connection timed out"
        except Exception as e:
            return False, 0, f"Health check failed: {str(e)}"

    def send_metrics(self, payload: Dict[str, Any]) -> Tuple[bool, int, str]:
        url = f"{self.settings.backend_url}/api/v1/metrics"
        try:
            verify_ssl = getattr(self.settings, "verify_ssl", True)
            with httpx.Client(timeout=self.timeout, transport=self.transport, verify=verify_ssl) as client:
                res = client.post(url, json=payload, headers=self._get_headers())
                if res.status_code in (200, 201, 208):
                    return True, res.status_code, res.text
                return False, res.status_code, res.text
        except httpx.ConnectError:
            return False, 0, "Backend unreachable: Connection refused"
        except httpx.TimeoutException:
            return False, 0, "Request timed out"
        except Exception as e:
            return False, 0, f"Network error: {str(e)}"

    def send_heartbeat(self, payload: Dict[str, Any]) -> Tuple[bool, int, str]:
        url = f"{self.settings.backend_url}/api/v1/heartbeat"
        try:
            verify_ssl = getattr(self.settings, "verify_ssl", True)
            with httpx.Client(timeout=self.timeout, transport=self.transport, verify=verify_ssl) as client:
                res = client.post(url, json=payload, headers=self._get_headers())
                if res.is_success:
                    return True, res.status_code, res.text
                return False, res.status_code, res.text
        except Exception as e:
            return False, 0, f"Heartbeat error: {str(e)}"
