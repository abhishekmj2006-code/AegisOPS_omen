import os
import time
import psutil
from typing import Dict, Optional, Tuple
from utils.logger import get_logger

logger = get_logger("DiskMonitor")


class DiskMonitor:
    """Monitors disk space usage and calculates read/write transfer rates."""

    def __init__(self, mount_point: Optional[str] = None) -> None:
        if mount_point:
            self.mount_point = mount_point
        elif os.name == "nt":
            self.mount_point = os.getenv("SystemDrive", "C:") + "\\"
        else:
            self.mount_point = "/"

        self.last_time: float = time.time()
        self.last_io: Optional[Tuple[int, int]] = self._get_raw_io_bytes()

    def _get_raw_io_bytes(self) -> Optional[Tuple[int, int]]:
        """Get cumulative disk read and write bytes."""
        try:
            counters = psutil.disk_io_counters()
            if counters:
                return counters.read_bytes, counters.write_bytes
        except Exception as e:
            logger.debug(f"Failed to fetch disk io counters: {e}")
        return None

    def collect_metrics(self) -> Dict[str, float]:
        """Collect disk percentage and I/O transfer rates in MB/s."""
        try:
            usage = psutil.disk_usage(self.mount_point)
            disk_pct = float(usage.percent)
            disk_pct = max(0.0, min(100.0, disk_pct))
        except Exception as e:
            logger.error(f"Error reading disk usage for {self.mount_point}: {e}")
            disk_pct = 0.0

        read_mbs = 0.0
        write_mbs = 0.0
        current_time = time.time()
        current_io = self._get_raw_io_bytes()

        if current_io and self.last_io:
            dt = max(0.1, current_time - self.last_time)
            read_diff = max(0, current_io[0] - self.last_io[0])
            write_diff = max(0, current_io[1] - self.last_io[1])
            read_mbs = round((read_diff / (1024 * 1024)) / dt, 2)
            write_mbs = round((write_diff / (1024 * 1024)) / dt, 2)

        self.last_time = current_time
        self.last_io = current_io

        return {
            "disk_usage": round(disk_pct, 2),
            "disk_read_mbs": read_mbs,
            "disk_write_mbs": write_mbs,
        }
