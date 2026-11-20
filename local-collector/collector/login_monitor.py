import os
import platform
import threading
import time
from typing import Optional, List, Dict, Any
from utils.logger import get_logger

logger = get_logger("LoginMonitor")


class LoginMonitor:
    """Monitors failed authentication attempts locally over a 60-second window.
    
    Guarantees local-first privacy:
    - Strips all IP addresses, usernames, and auth credentials.
    - Aggregates events within a rolling 60-second window.
    - Emits only allow-listed metadata: failed_login_count and security_threat_level.
    """

    def __init__(self, window_seconds: float = 60.0) -> None:
        self.window_seconds = window_seconds
        self._test_event_timestamps: List[float] = []
        self._lock = threading.Lock()
        self._native_supported = self._check_native_support()

    def _check_native_support(self) -> bool:
        if platform.system() != "Windows":
            return False
        try:
            import win32evtlog  # type: ignore
            hand = win32evtlog.OpenEventLog(None, "Security")
            win32evtlog.CloseEventLog(hand)
            logger.info("Native Windows Security Event Log access verified.")
            return True
        except Exception:
            logger.info("Using controlled local event stream for login monitoring.")
            return False

    def query_native_failed_logins(self) -> Optional[int]:
        if not self._native_supported:
            return None
        try:
            import win32evtlog  # type: ignore
            hand = win32evtlog.OpenEventLog(None, "Security")
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            total_failed = 0
            now = time.time()
            events = win32evtlog.ReadEventLog(hand, flags, 0)
            if events:
                for event in events:
                    # Windows Event ID 4625: An account failed to log on
                    event_id = event.EventID & 0xFFFF
                    if event_id == 4625:
                        # Only count events within the 60-second window
                        try:
                            ev_time = event.TimeGenerated.timestamp()
                            if now - ev_time <= self.window_seconds:
                                total_failed += 1
                        except Exception:
                            total_failed += 1
            win32evtlog.CloseEventLog(hand)
            return total_failed
        except Exception as e:
            logger.debug(f"Native event query error: {e}")
            return None

    def inject_test_failed_login(self, count: int = 1) -> int:
        """Inject failed login events into the 60s sliding window for testing."""
        now = time.time()
        with self._lock:
            for _ in range(max(1, count)):
                self._test_event_timestamps.append(now)
            logger.warning(f"Injected {count} failed login event(s) into 60s local window.")
            return len(self._test_event_timestamps)

    def _purge_stale_events(self, now: float) -> None:
        """Purge timestamps older than 60 seconds."""
        cutoff = now - self.window_seconds
        self._test_event_timestamps = [t for t in self._test_event_timestamps if t >= cutoff]

    def reset_counter(self) -> None:
        """Reset the simulated failed login counter."""
        with self._lock:
            self._test_event_timestamps.clear()

    def collect_metrics(self) -> int:
        """Return the current count of failed login attempts in the 60-second window."""
        metrics = self.collect_login_metrics()
        return metrics["failed_login_count"]

    def collect_login_metrics(self) -> Dict[str, Any]:
        """Aggregate failed logins over 60s window and determine security threat level."""
        now = time.time()
        with self._lock:
            self._purge_stale_events(now)
            sim_count = len(self._test_event_timestamps)

        native_count = self.query_native_failed_logins() or 0
        total_count = native_count + sim_count

        # Classify local threat level based on 60s burst threshold
        if total_count >= 3:
            threat_level = "critical"
        elif total_count >= 1:
            threat_level = "elevated"
        else:
            threat_level = "nominal"

        return {
            "failed_login_count": total_count,
            "security_threat_level": threat_level,
        }
