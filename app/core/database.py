"""Database connection and session management."""
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.core.config import settings

_is_sqlite = "sqlite" in settings.database_url

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {}
)

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables."""
    # Ensure database directory exists for SQLite
    if "sqlite" in settings.database_url:
        db_path = settings.database_url.replace("sqlite:///", "")
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    Base.metadata.create_all(bind=engine)

