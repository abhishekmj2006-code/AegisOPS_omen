from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from database.models import Base
from utils.logger import get_logger

logger = get_logger("Storage")


class DatabaseManager:
    """Manages SQLite database connection and thread-safe sessions."""

    def __init__(self, db_path: str = "local_collector.db") -> None:
        self.db_path = db_path
        self._ensure_dir()
        db_url = f"sqlite:///{Path(db_path).resolve()}"
        self.engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            echo=False,
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )
        self.init_db()

    def _ensure_dir(self) -> None:
        parent = Path(self.db_path).parent
        if parent and not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)

    def init_db(self) -> None:
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        session: Session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
