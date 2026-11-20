from datetime import datetime, timezone
import threading
import time
from typing import Callable, List, Optional
from config.settings import Settings
from communication.api_client import APIClient
from utils.logger import get_logger

logger = get_logger("ConnectionManager")


class ConnectionManager:
    """Monitors live backend connectivity status and triggers callbacks on state changes."""

    def __init__(self, settings: Settings, api_client: APIClient) -> None:
        self.settings = settings
        self.api_client = api_client
        self.is_online: bool = False
        self.last_successful_sync: Optional[datetime] = None
        self.last_status_code: int = 0
        self.last_error: Optional[str] = None
        self.status_text: str = "INITIALIZING"

        self._callbacks: List[Callable[[bool, str], None]] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def register_callback(self, cb: Callable[[bool, str], None]) -> None:
        with self._lock:
            self._callbacks.append(cb)

    def _notify(self) -> None:
        for cb in self._callbacks:
            try:
                cb(self.is_online, self.status_text)
            except Exception as e:
                logger.error(f"Error executing connection callback: {e}")

    def check_connection(self) -> bool:
        healthy, status_code, msg = self.api_client.check_health()
        with self._lock:
            old_online = self.is_online
            self.is_online = healthy
            self.last_status_code = status_code
            if healthy:
                self.status_text = "ONLINE"
                self.last_successful_sync = datetime.now(timezone.utc)
                self.last_error = None
            else:
                self.status_text = "OFFLINE"
                self.last_error = msg

        if old_online != self.is_online:
            self._notify()

        return self.is_online

    def start_background_monitoring(self, interval_seconds: float = 10.0) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval_seconds,),
            daemon=True,
            name="ConnectionMonitorThread"
        )
        self._thread.start()

    def _monitor_loop(self, interval: float) -> None:
        while not self._stop_event.is_set():
            try:
                self.check_connection()
            except Exception as e:
                logger.error(f"Exception in connection monitor loop: {e}")
            self._stop_event.wait(interval)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
