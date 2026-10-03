from __future__ import annotations

from dataclasses import dataclass

from app.database.database import session_scope
from app.database.repositories import admin_repo, button_repo
from app.utils.permissions import Role, admin_has_permission


@dataclass
class AdminView:
    id: int
    telegram_id: int
    role: str
    permissions: list[str]


def _to_view(admin) -> AdminView:
    return AdminView(
        id=admin.id,
        telegram_id=admin.telegram_id,
        role=admin.role,
        permissions=[p.permission for p in admin.permissions],
    )


def get_admin(telegram_id: int) -> AdminView | None:
    with session_scope() as session:
        admin = admin_repo.get_by_telegram_id(session, telegram_id)
        return _to_view(admin) if admin else None


def has_permission(telegram_id: int, permission: str) -> bool:
    with session_scope() as session:
        admin = admin_repo.get_by_telegram_id(session, telegram_id)
        return admin_has_permission(admin, permission)


def is_owner(telegram_id: int, owner_id: int) -> bool:
    return telegram_id == owner_id


def list_admins() -> list[AdminView]:
    with session_scope() as session:
        return [_to_view(a) for a in admin_repo.list_all(session)]


def add_admin(telegram_id: int, role: str, added_by: int) -> AdminView:
    with session_scope() as session:
        admin = admin_repo.create_admin(session, telegram_id, role, added_by)
        return _to_view(admin)


def remove_admin(admin_id: int) -> bool:
    with session_scope() as session:
        return admin_repo.delete_admin(session, admin_id)


def set_permission(admin_id: int, permission: str, granted: bool) -> AdminView | None:
    with session_scope() as session:
        admin = admin_repo.set_permission(session, admin_id, permission, granted)
        return _to_view(admin) if admin else None


# ---- Button tree helpers used by admin handlers ----

def build_tree_text(lang: str) -> str:
    """Render the whole button tree as indented text for the admin overview."""
    with session_scope() as session:
        all_buttons = button_repo.get_all(session)

    by_parent: dict[int | None, list] = {}
    for b in all_buttons:
        by_parent.setdefault(b.parent_id, []).append(b)
    for children in by_parent.values():
        children.sort(key=lambda b: (b.position, b.id))

    lines: list[str] = []

    def walk(parent_id, depth):
        for b in by_parent.get(parent_id, []):
            name = b.name_fa if lang == "fa" else b.name_en
            prefix = "  " * depth + ("└── " if depth else "")
            mark = "" if b.enabled else " 🚫"
            lines.append(f"{prefix}{name}{mark}")
            walk(b.id, depth + 1)

    walk(None, 0)
    return "\n".join(lines) if lines else ""
