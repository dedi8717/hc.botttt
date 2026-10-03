from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database.models import Admin, AdminPermission
from app.utils.permissions import DEFAULT_PERMISSIONS_BY_ROLE, Role


def get_by_telegram_id(session: Session, telegram_id: int) -> Admin | None:
    return session.execute(
        select(Admin)
        .options(selectinload(Admin.permissions))
        .where(Admin.telegram_id == telegram_id)
    ).scalar_one_or_none()


def get(session: Session, admin_id: int) -> Admin | None:
    return session.execute(
        select(Admin).options(selectinload(Admin.permissions)).where(Admin.id == admin_id)
    ).scalar_one_or_none()


def list_all(session: Session) -> list[Admin]:
    return (
        session.execute(select(Admin).options(selectinload(Admin.permissions)).order_by(Admin.created_at))
        .scalars()
        .all()
    )


def is_admin(session: Session, telegram_id: int) -> bool:
    return get_by_telegram_id(session, telegram_id) is not None


def ensure_owner(session: Session, owner_telegram_id: int) -> Admin:
    """Idempotently make sure the configured OWNER_ID has an OWNER admin row."""
    admin = get_by_telegram_id(session, owner_telegram_id)
    if admin:
        if admin.role != Role.OWNER.value:
            admin.role = Role.OWNER.value
        return admin
    admin = Admin(telegram_id=owner_telegram_id, role=Role.OWNER.value)
    session.add(admin)
    session.flush()
    _apply_default_permissions(session, admin)
    session.flush()
    return admin


def _apply_default_permissions(session: Session, admin: Admin) -> None:
    for perm in DEFAULT_PERMISSIONS_BY_ROLE.get(admin.role, []):
        session.add(AdminPermission(admin_id=admin.id, permission=perm))


def create_admin(
    session: Session, telegram_id: int, role: str, added_by: int, username: str | None = None
) -> Admin:
    existing = get_by_telegram_id(session, telegram_id)
    if existing:
        return existing
    admin = Admin(telegram_id=telegram_id, role=role, added_by=added_by, username=username)
    session.add(admin)
    session.flush()
    _apply_default_permissions(session, admin)
    session.flush()
    return admin


def delete_admin(session: Session, admin_id: int) -> bool:
    admin = get(session, admin_id)
    if not admin or admin.role == Role.OWNER.value:
        return False
    session.delete(admin)
    session.flush()
    return True


def set_permission(session: Session, admin_id: int, permission: str, granted: bool) -> Admin | None:
    admin = get(session, admin_id)
    if not admin or admin.role == Role.OWNER.value:
        return admin
    existing = next((p for p in admin.permissions if p.permission == permission), None)
    if granted and not existing:
        session.add(AdminPermission(admin_id=admin.id, permission=permission))
    elif not granted and existing:
        session.delete(existing)
    session.flush()
    return get(session, admin_id)
