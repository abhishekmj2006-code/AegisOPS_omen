"""Database connection management and initialization."""

from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from saas_config.settings import settings
from storage.models import Base, Tenant, CollectorNode

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialize database tables and seed baseline default tenants."""
    Base.metadata.create_all(bind=engine)

    # Lightweight migration check for existing SQLite databases
    with engine.connect() as conn:
        try:
            result = conn.execute(text("PRAGMA table_info(telemetry_records)"))
            cols = [row[1] for row in result.fetchall()]
            if cols and "source_timezone" not in cols:
                conn.execute(text("ALTER TABLE telemetry_records ADD COLUMN source_timezone VARCHAR(64) DEFAULT 'UTC'"))
                conn.commit()

            res_c = conn.execute(text("PRAGMA table_info(collector_nodes)"))
            c_cols = [row[1] for row in res_c.fetchall()]
            if c_cols:
                if "collector_cpu_overhead" not in c_cols:
                    conn.execute(text("ALTER TABLE collector_nodes ADD COLUMN collector_cpu_overhead FLOAT DEFAULT 0.2"))
                if "collector_ram_overhead" not in c_cols:
                    conn.execute(text("ALTER TABLE collector_nodes ADD COLUMN collector_ram_overhead FLOAT DEFAULT 24.5"))
                if "config_status" not in c_cols:
                    conn.execute(text("ALTER TABLE collector_nodes ADD COLUMN config_status VARCHAR(32) DEFAULT 'synced'"))
                conn.commit()

            res_i = conn.execute(text("PRAGMA table_info(incidents)"))
            i_cols = [row[1] for row in res_i.fetchall()]
            if i_cols:
                if "occurrence_count" not in i_cols:
                    conn.execute(text("ALTER TABLE incidents ADD COLUMN occurrence_count INTEGER DEFAULT 1"))
                if "last_seen_at" not in i_cols:
                    conn.execute(text("ALTER TABLE incidents ADD COLUMN last_seen_at DATETIME"))
                if "ai_engine" not in i_cols:
                    conn.execute(text("ALTER TABLE incidents ADD COLUMN ai_engine VARCHAR(64) DEFAULT 'Deterministic AIOps Engine'"))
                conn.commit()
        except Exception:
            pass

    # Seed default tenants for evaluation and multi-tenant testing
    with SessionLocal() as session:
        if not session.query(Tenant).filter_by(id="TENANT_001").first():
            t1 = Tenant(
                id="TENANT_001",
                name="Apex Global Enterprise (Production)",
                region="ap-south-1",
            )
            session.add(t1)
        
        if not session.query(Tenant).filter_by(id="TENANT_002").first():
            t2 = Tenant(
                id="TENANT_002",
                name="Meridian Financial Systems (Disaster Recovery)",
                region="eu-west-1",
            )
            session.add(t2)
            
        session.commit()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db():
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
