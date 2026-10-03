"""
SQLAlchemy engine / session management.

We use synchronous SQLAlchemy for simplicity (SQLite in dev). Handlers
call repository functions which open a short-lived session per call via
`session_scope()`. For a high-traffic deployment, swap the engine for an
async one (e.g. `sqlite+aiosqlite` or Postgres with asyncpg) and update
the repositories accordingly - the service layer above them does not
need to change.
"""
from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.config import config

connect_args = {"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(config.DATABASE_URL, connect_args=connect_args, future=True)

if config.DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, future=True, expire_on_commit=False
)


def init_db() -> None:
    """Create all tables. Call once on startup. For real migrations use Alembic."""
    from app.database import models  # noqa: F401  (ensure models are registered)

    models.Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
