from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database.models import Content


def get(session: Session, content_id: int) -> Content | None:
    return session.get(Content, content_id)


def get_for_button(session: Session, button_id: int) -> list[Content]:
    return (
        session.execute(
            select(Content).where(Content.button_id == button_id).order_by(Content.position, Content.id)
        )
        .scalars()
        .all()
    )


def next_position(session: Session, button_id: int) -> int:
    max_pos = session.execute(
        select(func.max(Content.position)).where(Content.button_id == button_id)
    ).scalar()
    return (max_pos or 0) + 1


def create(
    session: Session,
    button_id: int,
    content_type: str,
    text_fa: str | None = None,
    text_en: str | None = None,
    file_id: str | None = None,
    caption_fa: str | None = None,
    caption_en: str | None = None,
) -> Content:
    content = Content(
        button_id=button_id,
        content_type=content_type,
        text_fa=text_fa,
        text_en=text_en,
        file_id=file_id,
        caption_fa=caption_fa,
        caption_en=caption_en,
        position=next_position(session, button_id),
    )
    session.add(content)
    session.flush()
    return content


def update_text(session: Session, content_id: int, text_fa: str, text_en: str) -> Content | None:
    content = get(session, content_id)
    if content:
        content.text_fa = text_fa
        content.text_en = text_en
        session.flush()
    return content


def update_media(session: Session, content_id: int, file_id: str, content_type: str) -> Content | None:
    content = get(session, content_id)
    if content:
        content.file_id = file_id
        content.content_type = content_type
        session.flush()
    return content


def update_caption(session: Session, content_id: int, lang: str, caption: str) -> Content | None:
    content = get(session, content_id)
    if content:
        setattr(content, f"caption_{lang}", caption)
        session.flush()
    return content


def delete(session: Session, content_id: int) -> bool:
    content = get(session, content_id)
    if not content:
        return False
    session.delete(content)
    session.flush()
    return True


def move_position(session: Session, content_id: int, direction: str) -> bool:
    content = get(session, content_id)
    if not content:
        return False
    siblings = get_for_button(session, content.button_id)
    idx = next((i for i, c in enumerate(siblings) if c.id == content.id), None)
    if idx is None:
        return False
    if direction == "up" and idx > 0:
        other = siblings[idx - 1]
    elif direction == "down" and idx < len(siblings) - 1:
        other = siblings[idx + 1]
    else:
        return False
    content.position, other.position = other.position, content.position
    session.flush()
    return True
