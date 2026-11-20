"""SQLAlchemy database models for local persistent storage."""

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class QueuedMessage(Base):
    """Represents a message stored in SQLite for resilient delivery."""
    __tablename__ = "queued_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String(36), unique=True, nullable=False, index=True)
    payload_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    status = Column(String(20), default="PENDING", nullable=False, index=True) # PENDING, SENT, FAILED
    retry_count = Column(Integer, default=0, nullable=False)
    last_attempt_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    ack_response = Column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "message_id": self.message_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "status": self.status,
            "retry_count": self.retry_count,
            "last_attempt_at": self.last_attempt_at.isoformat() if self.last_attempt_at else None,
            "error_message": self.error_message,
        }
