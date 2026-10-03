from __future__ import annotations

from app.database.database import session_scope
from app.database.repositories import user_repo


def register_or_update(telegram_id: int, username: str | None, first_name: str | None):
    with session_scope() as session:
        user = user_repo.get_or_create(session, telegram_id, username, first_name)
        return user.id, user.language, user.is_blocked


def get_language(telegram_id: int) -> str | None:
    with session_scope() as session:
        user = user_repo.get_by_telegram_id(session, telegram_id)
        return user.language if user else None


def set_language(telegram_id: int, language: str) -> None:
    with session_scope() as session:
        user_repo.set_language(session, telegram_id, language)


def is_blocked(telegram_id: int) -> bool:
    with session_scope() as session:
        user = user_repo.get_by_telegram_id(session, telegram_id)
        return bool(user and user.is_blocked)


def stats() -> dict:
    with session_scope() as session:
        return {"total_users": user_repo.count_users(session)}
