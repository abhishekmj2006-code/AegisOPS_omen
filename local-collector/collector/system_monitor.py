import platform
import psutil
from typing import Dict, Any
from utils.logger import get_logger

logger = get_logger("SystemMonitor")


class SystemMonitor:
    """Collects CPU and RAM metrics with OS and hardware metadata."""

    def __init__(self) -> None:
        try:
            psutil.cpu_percent(interval=None)
        except Exception as e:
            logger.warning(f"Failed to initialize CPU baseline: {e}")

    def get_system_info(self) -> Dict[str, str]:
        """Return host OS and architecture metadata."""
        try:
            return {
                "os": platform.system(),
                "os_release": platform.release(),
                "os_version": platform.version(),
                "architecture": platform.machine(),
                "hostname": platform.node(),
                "processor": platform.processor() or "Unknown",
            }
        except Exception as e:
            logger.error(f"Error gathering system info: {e}")
            return {
                "os": "Unknown",
                "os_release": "",
                "os_version": "",
                "architecture": "",
                "hostname": "localhost",
                "processor": "",
            }

    def collect_metrics(self) -> Dict[str, float]:
        """Collect real-time CPU and RAM metrics."""
        try:
            cpu_pct = float(psutil.cpu_percent(interval=None))
            cpu_pct = max(0.0, min(100.0, cpu_pct))
        except Exception as e:
            logger.error(f"Error reading CPU usage: {e}")
            cpu_pct = 0.0

        try:
            vm = psutil.virtual_memory()
            ram_pct = float(vm.percent)
            ram_pct = max(0.0, min(100.0, ram_pct))
            total_gb = round(vm.total / (1024 ** 3), 2)
            avail_gb = round(vm.available / (1024 ** 3), 2)
        except Exception as e:
            logger.error(f"Error reading RAM usage: {e}")
            ram_pct = 0.0
            total_gb = 0.0
            avail_gb = 0.0

        return {
            "cpu_usage": round(cpu_pct, 2),
            "ram_usage": round(ram_pct, 2),
            "ram_total_gb": total_gb,
            "ram_available_gb": avail_gb,
        }
