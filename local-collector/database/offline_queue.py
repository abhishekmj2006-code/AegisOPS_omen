from datetime import datetime, timezone
import json
import threading
from typing import Any, Dict, List, Optional
from sqlalchemy import case, desc

from database.models import QueuedMessage
from database.storage import DatabaseManager
from utils.logger import get_logger

logger = get_logger("OfflineQueue")


class OfflineQueue:
    """Thread-safe persistent offline message queue backed by SQLite."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager
        self._lock = threading.Lock()

    def enqueue(self, payload: Dict[str, Any]) -> QueuedMessage:
        message_id = payload["message_id"]
        payload_str = json.dumps(payload)

        with self._lock:
            with self.db.get_session() as session:
                existing = session.query(QueuedMessage).filter_by(message_id=message_id).first()
                if existing:
                    return existing

                record = QueuedMessage(
                    message_id=message_id,
                    payload_json=payload_str,
                    created_at=datetime.now(timezone.utc),
                    status="PENDING",
                    retry_count=0,
                )
                session.add(record)
                session.flush()
                session.refresh(record)
                logger.info(f"Enqueued message {message_id} to offline storage")
                return record

    def get_pending_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            with self.db.get_session() as session:
                records = (
                    session.query(QueuedMessage)
                    .filter_by(status="PENDING")
                    .order_by(QueuedMessage.created_at.asc())
                    .limit(limit)
                    .all()
                )
                results = []
                for r in records:
                    try:
                        payload = json.loads(r.payload_json)
                        results.append({
                            "id": r.id,
                            "message_id": r.message_id,
                            "payload": payload,
                            "retry_count": r.retry_count,
                            "created_at": r.created_at,
                        })
                    except Exception as e:
                        logger.error(f"Error parsing queued payload {r.message_id}: {e}")
                return results

    def mark_as_sent(self, message_id: str, ack_response: str = "") -> bool:
        with self._lock:
            with self.db.get_session() as session:
                record = session.query(QueuedMessage).filter_by(message_id=message_id).first()
                if record:
                    record.status = "SENT"
                    record.last_attempt_at = datetime.now(timezone.utc)
                    record.ack_response = ack_response[:500] if ack_response else None
                    record.error_message = None
                    logger.info(f"Acknowledged delivery for message {message_id}")
                    return True
                return False

    def mark_as_failed(self, message_id: str, error_message: str) -> None:
        with self._lock:
            with self.db.get_session() as session:
                record = session.query(QueuedMessage).filter_by(message_id=message_id).first()
                if record:
                    record.retry_count += 1
                    record.last_attempt_at = datetime.now(timezone.utc)
                    record.error_message = error_message[:500]
                    logger.warning(
                        f"Message {message_id} delivery failed (attempt {record.retry_count}): {error_message}"
                    )

    def get_stats(self) -> Dict[str, int]:
        with self._lock:
            with self.db.get_session() as session:
                pending = session.query(QueuedMessage).filter_by(status="PENDING").count()
                sent = session.query(QueuedMessage).filter_by(status="SENT").count()
                failed = session.query(QueuedMessage).filter(
                    QueuedMessage.status == "PENDING", QueuedMessage.retry_count > 0
                ).count()
                total = session.query(QueuedMessage).count()
                return {
                    "pending": pending,
                    "sent": sent,
                    "failed_attempts": failed,
                    "total": total,
                }

    def get_recent_messages(self, limit: int = 35) -> List[Dict[str, Any]]:
        with self._lock:
            with self.db.get_session() as session:
                records = (
                    session.query(QueuedMessage)
                    .order_by(
                        case((QueuedMessage.status == "PENDING", 0), else_=1),
                        desc(QueuedMessage.created_at)
                    )
                    .limit(limit)
                    .all()
                )
                return [r.to_dict() for r in records]

    def clear_all(self) -> int:
        """Reset entire queue to 0 records."""
        with self._lock:
            with self.db.get_session() as session:
                deleted = session.query(QueuedMessage).delete()
                logger.info("Cleared all offline queue records from SQLite.")
                return deleted

    def clear_sent(self) -> int:
        with self._lock:
            with self.db.get_session() as session:
                deleted = session.query(QueuedMessage).filter_by(status="SENT").delete()
                return deleted
