from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import User


def get_by_telegram_id(session: Session, telegram_id: int) -> User | None:
    return session.execute(
        select(User).where(User.telegram_id == telegram_id)
    ).scalar_one_or_none()


def get_or_create(session: Session, telegram_id: int, username: str | None, first_name: str | None) -> User:
    user = get_by_telegram_id(session, telegram_id)
    if user:
        changed = False
        if user.username != username:
            user.username = username
            changed = True
        if user.first_name != first_name:
            user.first_name = first_name
            changed = True
        if changed:
            session.flush()
        return user

    user = User(telegram_id=telegram_id, username=username, first_name=first_name)
    session.add(user)
    session.flush()
    return user


def set_language(session: Session, telegram_id: int, language: str) -> User | None:
    user = get_by_telegram_id(session, telegram_id)
    if user:
        user.language = language
        session.flush()
    return user


def set_blocked(session: Session, telegram_id: int, blocked: bool) -> User | None:
    user = get_by_telegram_id(session, telegram_id)
    if user:
        user.is_blocked = blocked
        session.flush()
    return user


def count_users(session: Session) -> int:
    return session.query(User).count()


def list_users(session: Session, limit: int = 50, offset: int = 0) -> list[User]:
    return (
        session.execute(select(User).order_by(User.created_at.desc()).limit(limit).offset(offset))
        .scalars()
        .all()
    )


def get_all_telegram_ids(session: Session, exclude_blocked: bool = True) -> list[int]:
    stmt = select(User.telegram_id)
    if exclude_blocked:
        stmt = stmt.where(User.is_blocked == False)  # noqa: E712
    return session.execute(stmt).scalars().all()
