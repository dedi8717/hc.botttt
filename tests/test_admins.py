from app.database.database import session_scope
from app.database.repositories import admin_repo
from app.utils.permissions import Role


def test_create_admin_with_default_permissions():
    with session_scope() as session:
        admin = admin_repo.create_admin(session, 555001, Role.ADMIN.value, added_by=1)
        perms = {p.permission for p in admin.permissions}
        assert "manage_buttons" in perms
        assert "manage_admins" not in perms  # not granted to plain ADMIN by default


def test_create_moderator_has_limited_permissions():
    with session_scope() as session:
        admin = admin_repo.create_admin(session, 555002, Role.MODERATOR.value, added_by=1)
        perms = {p.permission for p in admin.permissions}
        assert "manage_content" in perms
        assert "manage_admins" not in perms
        assert "manage_buttons" not in perms


def test_delete_admin():
    with session_scope() as session:
        admin = admin_repo.create_admin(session, 555003, Role.ADMIN.value, added_by=1)
        admin_id = admin.id

    with session_scope() as session:
        assert admin_repo.delete_admin(session, admin_id) is True
        assert admin_repo.get(session, admin_id) is None


def test_owner_cannot_be_deleted(owner_id):
    with session_scope() as session:
        owner = admin_repo.get_by_telegram_id(session, owner_id)
        assert admin_repo.delete_admin(session, owner.id) is False
        # owner still present
        assert admin_repo.get_by_telegram_id(session, owner_id) is not None
