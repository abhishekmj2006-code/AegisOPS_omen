import os
import re
import socket
import subprocess
import time
import psutil
from typing import Dict, Optional, Tuple
from utils.logger import get_logger

logger = get_logger("NetworkMonitor")


class NetworkMonitor:
    """Measures network upload/download speeds, latency, and packet loss."""

    def __init__(self, target_host: str = "8.8.8.8", target_port: int = 53) -> None:
        self.target_host = target_host
        self.target_port = target_port
        self.last_time: float = time.time()
        self.last_net_io: Optional[Tuple[int, int]] = self._get_raw_net_bytes()

    def set_target(self, host: str, port: int = 53) -> None:
        """Update latency measurement target."""
        self.target_host = host
        self.target_port = port

    def _get_raw_net_bytes(self) -> Optional[Tuple[int, int]]:
        """Get cumulative bytes sent and received."""
        try:
            counters = psutil.net_io_counters()
            if counters:
                return counters.bytes_sent, counters.bytes_recv
        except Exception as e:
            logger.debug(f"Failed to fetch net io counters: {e}")
        return None

    def measure_latency_socket(self, samples: int = 2, timeout: float = 1.0) -> Tuple[float, float]:
        """Measure round-trip latency (ms) and packet loss (%) using safe TCP socket connect."""
        latencies = []
        lost = 0

        for _ in range(samples):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            start = time.perf_counter()
            try:
                sock.connect((self.target_host, self.target_port))
                rtt = (time.perf_counter() - start) * 1000.0
                latencies.append(rtt)
            except (socket.timeout, socket.error):
                lost += 1
            finally:
                sock.close()

        packet_loss = round((lost / samples) * 100.0, 2)
        avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
        return avg_latency, packet_loss

    def measure_latency_ping(self) -> Optional[Tuple[float, float]]:
        """Attempt system ping command as secondary probe where supported."""
        try:
            is_win = os.name == "nt"
            cmd = ["ping", "-n", "2", "-w", "1000", self.target_host] if is_win else ["ping", "-c", "2", "-W", "1", self.target_host]
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=3.0,
            )
            if result.returncode == 0:
                match = re.search(r"Average = (\d+)ms", result.stdout, re.IGNORECASE)
                if not match:
                    match = re.search(r"/([\d.]+)/", result.stdout)
                
                loss_match = re.search(r"(\d+)% loss", result.stdout, re.IGNORECASE)
                loss_pct = float(loss_match.group(1)) if loss_match else 0.0

                if match:
                    latency_ms = float(match.group(1))
                    return latency_ms, loss_pct
        except Exception:
            pass
        return None

    def collect_metrics(self) -> Dict[str, float]:
        """Collect upload/download speed (KB/s), latency (ms), and packet loss (%)."""
        current_time = time.time()
        current_net_io = self._get_raw_net_bytes()
        up_kbps = 0.0
        down_kbps = 0.0

        if current_net_io and self.last_net_io:
            dt = max(0.1, current_time - self.last_time)
            sent_diff = max(0, current_net_io[0] - self.last_net_io[0])
            recv_diff = max(0, current_net_io[1] - self.last_net_io[1])
            up_kbps = round((sent_diff / 1024.0) / dt, 2)
            down_kbps = round((recv_diff / 1024.0) / dt, 2)

        self.last_time = current_time
        self.last_net_io = current_net_io

        probe_res = self.measure_latency_ping()
        if probe_res is not None:
            latency_ms, packet_loss = probe_res
        else:
            latency_ms, packet_loss = self.measure_latency_socket()

        return {
            "network_upload_kbps": up_kbps,
            "network_download_kbps": down_kbps,
            "network_latency_ms": latency_ms,
            "packet_loss_percent": packet_loss,
        }
