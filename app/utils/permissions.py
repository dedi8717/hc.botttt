"""
Role / Permission system.

Roles:
    OWNER      - full access to everything, cannot be removed or demoted.
    ADMIN      - regular administrative access (customizable permission set).
    MODERATOR  - limited access (customizable permission set).

Permissions are individual capability flags stored per-admin in the
`admin_permissions` table, so they can be toggled independently of role.
The role only controls the *default* set of permissions granted when an
admin is created, plus a few hard rules (e.g. only OWNER may manage admins
or touch the owner account).
"""
from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MODERATOR = "MODERATOR"


class Permission(str, Enum):
    MANAGE_BUTTONS = "manage_buttons"
    MANAGE_CONTENT = "manage_content"
    MANAGE_PRICES = "manage_prices"
    MANAGE_USERS = "manage_users"
    MANAGE_PAYMENTS = "manage_payments"
    MANAGE_ADMINS = "manage_admins"
    VIEW_STATISTICS = "view_statistics"


ALL_PERMISSIONS = [p.value for p in Permission]

# Permissions considered "sensitive" - only the OWNER may grant/revoke them
# or manage admins who hold them.
SENSITIVE_PERMISSIONS = {Permission.MANAGE_ADMINS.value}

DEFAULT_PERMISSIONS_BY_ROLE = {
    Role.OWNER.value: ALL_PERMISSIONS,
    Role.ADMIN.value: [
        Permission.MANAGE_BUTTONS.value,
        Permission.MANAGE_CONTENT.value,
        Permission.MANAGE_PRICES.value,
        Permission.MANAGE_USERS.value,
        Permission.VIEW_STATISTICS.value,
    ],
    Role.MODERATOR.value: [
        Permission.MANAGE_CONTENT.value,
        Permission.VIEW_STATISTICS.value,
    ],
}


def admin_has_permission(admin, permission: str) -> bool:
    """`admin` is a database Admin model instance (or None)."""
    if admin is None:
        return False
    if admin.role == Role.OWNER.value:
        return True
    granted = {p.permission for p in admin.permissions}
    return permission in granted
