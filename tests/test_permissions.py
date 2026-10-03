from app.database.database import session_scope
from app.database.repositories import admin_repo
from app.utils.permissions import Permission, Role, admin_has_permission


def test_owner_has_every_permission(owner_id):
    with session_scope() as session:
        owner = admin_repo.get_by_telegram_id(session, owner_id)
        for perm in Permission:
            assert admin_has_permission(owner, perm.value) is True


def test_admin_without_permission_denied():
    with session_scope() as session:
        admin = admin_repo.create_admin(session, 555010, Role.MODERATOR.value, added_by=1)
        assert admin_has_permission(admin, Permission.MANAGE_ADMINS.value) is False
        assert admin_has_permission(admin, Permission.MANAGE_CONTENT.value) is True


def test_toggle_permission_grant_and_revoke():
    with session_scope() as session:
        admin = admin_repo.create_admin(session, 555011, Role.MODERATOR.value, added_by=1)
        admin_id = admin.id

    with session_scope() as session:
        admin_repo.set_permission(session, admin_id, Permission.MANAGE_BUTTONS.value, True)
        admin = admin_repo.get(session, admin_id)
        assert admin_has_permission(admin, Permission.MANAGE_BUTTONS.value) is True

    with session_scope() as session:
        admin_repo.set_permission(session, admin_id, Permission.MANAGE_BUTTONS.value, False)
        admin = admin_repo.get(session, admin_id)
        assert admin_has_permission(admin, Permission.MANAGE_BUTTONS.value) is False


def test_none_admin_has_no_permission():
    assert admin_has_permission(None, Permission.MANAGE_CONTENT.value) is False
