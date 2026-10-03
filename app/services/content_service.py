from __future__ import annotations

from app.database.database import session_scope
from app.database.repositories import content_repo


def add_text(button_id: int, text_fa: str, text_en: str) -> int:
    with session_scope() as session:
        content = content_repo.create(session, button_id, "text", text_fa=text_fa, text_en=text_en)
        return content.id


def add_media(button_id: int, content_type: str, file_id: str) -> int:
    with session_scope() as session:
        content = content_repo.create(session, button_id, content_type, file_id=file_id)
        return content.id


def set_caption(content_id: int, lang: str, caption: str) -> None:
    with session_scope() as session:
        content_repo.update_caption(session, content_id, lang, caption)


def update_text(content_id: int, text_fa: str, text_en: str) -> None:
    with session_scope() as session:
        content_repo.update_text(session, content_id, text_fa, text_en)


def update_media(content_id: int, file_id: str, content_type: str) -> None:
    with session_scope() as session:
        content_repo.update_media(session, content_id, file_id, content_type)


def delete(content_id: int) -> bool:
    with session_scope() as session:
        return content_repo.delete(session, content_id)


def move(content_id: int, direction: str) -> bool:
    with session_scope() as session:
        return content_repo.move_position(session, content_id, direction)


def get(content_id: int):
    with session_scope() as session:
        return content_repo.get(session, content_id)
