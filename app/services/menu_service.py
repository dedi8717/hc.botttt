"""
Reads the dynamic menu (Button tree) from the database.

Handlers should never query app.database.models directly - they go
through this service (and the repositories it wraps) so the menu shown
to users always reflects the database, never anything hard-coded.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.database.database import session_scope
from app.database.repositories import button_repo, content_repo
from app.utils.translations import field_for_lang


@dataclass
class ButtonView:
    id: int
    parent_id: int | None
    name: str
    enabled: bool
    is_free: bool
    price: int
    currency: str
    has_children: bool
    has_content: bool


@dataclass
class ContentView:
    id: int
    content_type: str
    text: str | None
    file_id: str | None
    caption: str | None


def get_children(parent_id: int | None, lang: str, only_enabled: bool = True) -> list[ButtonView]:
    with session_scope() as session:
        buttons = button_repo.get_children(session, parent_id, only_enabled=only_enabled)
        result = []
        for b in buttons:
            result.append(
                ButtonView(
                    id=b.id,
                    parent_id=b.parent_id,
                    name=field_for_lang(b, "name", lang),
                    enabled=b.enabled,
                    is_free=b.is_free,
                    price=b.price,
                    currency=b.currency,
                    has_children=button_repo.has_children(session, b.id),
                    has_content=len(content_repo.get_for_button(session, b.id)) > 0,
                )
            )
        return result


def get_button(button_id: int, lang: str) -> ButtonView | None:
    with session_scope() as session:
        b = button_repo.get(session, button_id)
        if not b:
            return None
        return ButtonView(
            id=b.id,
            parent_id=b.parent_id,
            name=field_for_lang(b, "name", lang),
            enabled=b.enabled,
            is_free=b.is_free,
            price=b.price,
            currency=b.currency,
            has_children=button_repo.has_children(session, b.id),
            has_content=len(content_repo.get_for_button(session, b.id)) > 0,
        )


def get_contents(button_id: int, lang: str) -> list[ContentView]:
    with session_scope() as session:
        contents = content_repo.get_for_button(session, button_id)
        result = []
        for c in contents:
            text = field_for_lang(c, "text", lang) if c.content_type == "text" else None
            caption = field_for_lang(c, "caption", lang) if c.content_type != "text" else None
            result.append(
                ContentView(
                    id=c.id,
                    content_type=c.content_type,
                    text=text or None,
                    file_id=c.file_id,
                    caption=caption or None,
                )
            )
        return result


def build_breadcrumb_root(button_id: int | None) -> int | None:
    """Return the parent_id of the given button (for the Back button), or None if at root."""
    if button_id is None:
        return None
    with session_scope() as session:
        b = button_repo.get(session, button_id)
        return b.parent_id if b else None
