from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database.models import Button


def get(session: Session, button_id: int) -> Button | None:
    return session.get(Button, button_id)


def get_children(session: Session, parent_id: int | None, only_enabled: bool = False) -> list[Button]:
    stmt = select(Button).where(Button.parent_id == parent_id).order_by(Button.position, Button.id)
    if only_enabled:
        stmt = stmt.where(Button.enabled == True)  # noqa: E712
    return session.execute(stmt).scalars().all()


def get_all(session: Session) -> list[Button]:
    return session.execute(select(Button).order_by(Button.parent_id, Button.position)).scalars().all()


def next_position(session: Session, parent_id: int | None) -> int:
    max_pos = session.execute(
        select(func.max(Button.position)).where(Button.parent_id == parent_id)
    ).scalar()
    return (max_pos or 0) + 1


def create(
    session: Session,
    name_fa: str,
    name_en: str,
    parent_id: int | None = None,
    is_free: bool = True,
    price: int = 0,
    currency: str = "XTR",
) -> Button:
    button = Button(
        name_fa=name_fa,
        name_en=name_en,
        parent_id=parent_id,
        position=next_position(session, parent_id),
        is_free=is_free,
        price=price,
        currency=currency,
        enabled=True,
    )
    session.add(button)
    session.flush()
    return button


def rename(session: Session, button_id: int, name_fa: str, name_en: str) -> Button | None:
    button = get(session, button_id)
    if button:
        button.name_fa = name_fa
        button.name_en = name_en
        session.flush()
    return button


def set_price(session: Session, button_id: int, price: int, currency: str | None = None) -> Button | None:
    button = get(session, button_id)
    if button:
        button.price = price
        if currency:
            button.currency = currency
        button.is_free = price <= 0
        session.flush()
    return button


def set_free(session: Session, button_id: int, is_free: bool) -> Button | None:
    button = get(session, button_id)
    if button:
        button.is_free = is_free
        session.flush()
    return button


def toggle_enabled(session: Session, button_id: int) -> Button | None:
    button = get(session, button_id)
    if button:
        button.enabled = not button.enabled
        session.flush()
    return button


def delete(session: Session, button_id: int) -> bool:
    button = get(session, button_id)
    if not button:
        return False
    session.delete(button)  # cascades to children + contents via relationship config
    session.flush()
    return True


def is_descendant(session: Session, button_id: int, potential_ancestor_id: int) -> bool:
    """True if `potential_ancestor_id` is button_id itself or a descendant of button_id.

    Used to prevent circular parent references when moving a button.
    """
    if button_id == potential_ancestor_id:
        return True
    children = get_children(session, button_id)
    for child in children:
        if is_descendant(session, child.id, potential_ancestor_id):
            return True
    return False


def move_to_parent(session: Session, button_id: int, new_parent_id: int | None) -> tuple[bool, str]:
    if new_parent_id is not None:
        if new_parent_id == button_id:
            return False, "circular"
        if is_descendant(session, button_id, new_parent_id):
            return False, "circular"
        if get(session, new_parent_id) is None:
            return False, "not_found"

    button = get(session, button_id)
    if not button:
        return False, "not_found"
    button.parent_id = new_parent_id
    button.position = next_position(session, new_parent_id)
    session.flush()
    return True, "ok"


def move_position(session: Session, button_id: int, direction: str) -> bool:
    """direction: 'up' or 'down'. Swaps position with the adjacent sibling."""
    button = get(session, button_id)
    if not button:
        return False
    siblings = get_children(session, button.parent_id)
    idx = next((i for i, b in enumerate(siblings) if b.id == button.id), None)
    if idx is None:
        return False
    if direction == "up" and idx > 0:
        other = siblings[idx - 1]
    elif direction == "down" and idx < len(siblings) - 1:
        other = siblings[idx + 1]
    else:
        return False
    button.position, other.position = other.position, button.position
    session.flush()
    return True


def has_children(session: Session, button_id: int) -> bool:
    return session.execute(
        select(func.count()).select_from(Button).where(Button.parent_id == button_id)
    ).scalar() > 0
