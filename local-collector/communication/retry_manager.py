import random
import threading
import time
from typing import Dict, Optional, Tuple
from database.offline_queue import OfflineQueue
from communication.api_client import APIClient
from communication.connection_manager import ConnectionManager
from utils.logger import get_logger

logger = get_logger("RetryManager")


class RetryManager:
    """Manages resilient transmission of queued messages with exponential backoff and jitter."""

    def __init__(
        self,
        offline_queue: OfflineQueue,
        api_client: APIClient,
        connection_manager: ConnectionManager,
        base_delay: float = 2.0,
        max_delay: float = 60.0,
    ) -> None:
        self.queue = offline_queue
        self.api_client = api_client
        self.conn_mgr = connection_manager
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._is_flushing = False
        self._lock = threading.Lock()

    def calculate_backoff(self, retry_count: int) -> float:
        factor = 2 ** min(retry_count, 6)
        delay = min(self.base_delay * factor, self.max_delay)
        jitter = random.uniform(0.1, 0.25) * delay
        return delay + jitter

    def process_pending_queue(self, max_batch: int = 50) -> Tuple[int, int]:
        with self._lock:
            if self._is_flushing:
                return 0, 0
            self._is_flushing = True

        sent_count = 0
        failed_count = 0

        try:
            pending_items = self.queue.get_pending_messages(limit=max_batch)
            if not pending_items:
                return 0, 0

            logger.info(f"Processing offline queue: {len(pending_items)} pending message(s)")

            for item in pending_items:
                message_id = item["message_id"]
                payload = item["payload"]
                retry_count = item["retry_count"]

                success, status_code, response_text = self.api_client.send_metrics(payload)

                if success:
                    self.queue.mark_as_sent(message_id, ack_response=f"HTTP {status_code}: {response_text}")
                    sent_count += 1
                    self.conn_mgr.is_online = True
                    self.conn_mgr.status_text = "ONLINE"
                else:
                    self.queue.mark_as_failed(message_id, error_message=f"HTTP {status_code}: {response_text}")
                    failed_count += 1
                    self.conn_mgr.is_online = False
                    self.conn_mgr.status_text = "OFFLINE"
                    if status_code == 0:
                        break

            logger.info(f"Offline queue pass complete: {sent_count} sent, {failed_count} failed")
            return sent_count, failed_count
        finally:
            with self._lock:
                self._is_flushing = False
