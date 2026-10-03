from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.models import Settings


def get(session: Session, key: str) -> str | None:
    row = session.get(Settings, key)
    return row.value if row else None


def set(session: Session, key: str, value: str) -> None:
    row = session.get(Settings, key)
    if row:
        row.value = value
    else:
        row = Settings(key=key, value=value)
        session.add(row)
    session.flush()
