from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.admin_service import AdminView
from app.services.menu_service import ButtonView, ContentView
from app.services.payment_method_service import PaymentMethodView
from app.utils.helpers import truncate
from app.utils.permissions import ALL_PERMISSIONS, Role
from app.utils.translations import t


def admin_panel_keyboard(lang: str, perms: set[str], is_owner: bool) -> InlineKeyboardMarkup:
    rows = []
    if is_owner or "manage_buttons" in perms:
        rows.append([InlineKeyboardButton(t("admin_manage_buttons", lang), callback_data="admin:buttons:root")])
    if is_owner or "manage_admins" in perms:
        rows.append([InlineKeyboardButton(t("admin_manage_admins", lang), callback_data="admin:admins:root")])
    if is_owner or "manage_users" in perms:
        rows.append([InlineKeyboardButton(t("admin_users", lang), callback_data="admin:users:root")])
        rows.append([InlineKeyboardButton(t("admin_send_message", lang), callback_data="admin:message:root")])
    if is_owner or "view_statistics" in perms:
        rows.append([InlineKeyboardButton(t("admin_stats", lang), callback_data="admin:stats:root")])
    if is_owner or "manage_payments" in perms:
        rows.append([InlineKeyboardButton(t("admin_payment_methods", lang), callback_data="admin:paymethods:root")])
        rows.append([InlineKeyboardButton(t("admin_settings", lang), callback_data="admin:settings:root")])
    return InlineKeyboardMarkup(rows)


def buttons_root_keyboard(lang: str, buttons: list[ButtonView]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(t("btn_add", lang), callback_data="admin:buttons:add:0")]]
    for b in buttons:
        mark = "" if b.enabled else " \U0001F6AB"
        rows.append(
            [InlineKeyboardButton(truncate(b.name) + mark, callback_data=f"admin:buttons:view:{b.id}")]
        )
    rows.append([InlineKeyboardButton(t("back", lang), callback_data="admin:root")])
    return InlineKeyboardMarkup(rows)


def button_manage_keyboard(lang: str, button: ButtonView) -> InlineKeyboardMarkup:
    price_row_label = t("btn_make_paid", lang) if button.is_free else t("btn_make_free", lang)
    rows = [
        [InlineKeyboardButton(t("btn_rename", lang), callback_data=f"admin:buttons:rename:{button.id}")],
        [InlineKeyboardButton(t("btn_manage_content", lang), callback_data=f"admin:content:root:{button.id}")],
        [InlineKeyboardButton(t("btn_add_child", lang), callback_data=f"admin:buttons:add:{button.id}")],
        [InlineKeyboardButton(t("btn_set_price", lang), callback_data=f"admin:buttons:price:{button.id}")],
        [InlineKeyboardButton(price_row_label, callback_data=f"admin:buttons:freetoggle:{button.id}")],
        [InlineKeyboardButton(t("btn_payment_methods", lang), callback_data=f"admin:buttons:paymethods:{button.id}")],
        [
            InlineKeyboardButton(t("btn_move_up", lang), callback_data=f"admin:buttons:move:{button.id}:up"),
            InlineKeyboardButton(t("btn_move_down", lang), callback_data=f"admin:buttons:move:{button.id}:down"),
        ],
        [InlineKeyboardButton(t("btn_toggle", lang), callback_data=f"admin:buttons:toggle:{button.id}")],
        [InlineKeyboardButton(t("btn_move_parent", lang), callback_data=f"admin:buttons:moveparent:{button.id}")],
        [InlineKeyboardButton(t("btn_delete", lang), callback_data=f"admin:buttons:delete:{button.id}")],
        [
            InlineKeyboardButton(
                t("back", lang),
                callback_data=f"admin:buttons:view:{button.parent_id}"
                if button.parent_id
                else "admin:buttons:root",
            )
        ],
    ]
    return InlineKeyboardMarkup(rows)


def button_parent_choice_keyboard(lang: str, buttons: list[ButtonView], prefix: str) -> InlineKeyboardMarkup:
    """prefix e.g. 'admin:buttons:setparent' - each row calls f'{prefix}:{button_id_or_0}'"""
    rows = [[InlineKeyboardButton(t("root_menu_option", lang), callback_data=f"{prefix}:0")]]
    for b in buttons:
        rows.append([InlineKeyboardButton(truncate(b.name), callback_data=f"{prefix}:{b.id}")])
    return InlineKeyboardMarkup(rows)


def content_root_keyboard(lang: str, button_id: int, contents: list[ContentView]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(t("content_add", lang), callback_data=f"admin:content:add:{button_id}")],
    ]
    if contents:
        rows.append([InlineKeyboardButton(t("content_edit", lang), callback_data=f"admin:content:editlist:{button_id}")])
        rows.append([InlineKeyboardButton(t("content_delete", lang), callback_data=f"admin:content:dellist:{button_id}")])
        rows.append([InlineKeyboardButton(t("content_move", lang), callback_data=f"admin:content:movelist:{button_id}")])
    rows.append([InlineKeyboardButton(t("back", lang), callback_data=f"admin:buttons:view:{button_id}")])
    return InlineKeyboardMarkup(rows)


def content_list_keyboard(lang: str, button_id: int, contents: list[ContentView], action: str) -> InlineKeyboardMarkup:
    """action: 'edit' | 'delete' | 'move'"""
    icons = {"text": "\U0001F4DD", "photo": "\U0001F5BC", "video": "\U0001F3A5", "document": "\U0001F4C1"}
    rows = []
    for c in contents:
        label = f"{icons.get(c.content_type, '')} {truncate(c.text or c.caption or c.content_type, 30)}"
        rows.append([InlineKeyboardButton(label, callback_data=f"admin:content:{action}:{c.id}")])
    rows.append([InlineKeyboardButton(t("back", lang), callback_data=f"admin:content:root:{button_id}")])
    return InlineKeyboardMarkup(rows)


def content_edit_field_keyboard(lang: str, content: ContentView) -> InlineKeyboardMarkup:
    rows = []
    if content.content_type == "text":
        rows.append([InlineKeyboardButton(t("edit_text", lang), callback_data=f"admin:content:editfield:{content.id}:text")])
    else:
        rows.append([InlineKeyboardButton(t("edit_media", lang), callback_data=f"admin:content:editfield:{content.id}:media")])
        rows.append([InlineKeyboardButton(t("edit_caption_fa", lang), callback_data=f"admin:content:editfield:{content.id}:caption_fa")])
        rows.append([InlineKeyboardButton(t("edit_caption_en", lang), callback_data=f"admin:content:editfield:{content.id}:caption_en")])
    rows.append([InlineKeyboardButton(t("back", lang), callback_data="admin:content:editcancel")])
    return InlineKeyboardMarkup(rows)


def move_up_down_keyboard(lang: str, item_id: int, action_prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(t("btn_move_up", lang), callback_data=f"{action_prefix}:{item_id}:up"),
                InlineKeyboardButton(t("btn_move_down", lang), callback_data=f"{action_prefix}:{item_id}:down"),
            ]
        ]
    )


def admins_panel_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(t("admin_add", lang), callback_data="admin:admins:add")],
            [InlineKeyboardButton(t("admin_list", lang), callback_data="admin:admins:list")],
            [InlineKeyboardButton(t("back", lang), callback_data="admin:root")],
        ]
    )


def admins_list_keyboard(lang: str, admins: list[AdminView], owner_id: int) -> InlineKeyboardMarkup:
    rows = []
    for a in admins:
        label = f"{a.telegram_id} ({a.role})"
        rows.append([InlineKeyboardButton(label, callback_data=f"admin:admins:view:{a.id}")])
    rows.append([InlineKeyboardButton(t("back", lang), callback_data="admin:admins:root")])
    return InlineKeyboardMarkup(rows)


def admin_view_keyboard(lang: str, admin: AdminView, owner_id: int) -> InlineKeyboardMarkup:
    rows = []
    if admin.telegram_id != owner_id:
        rows.append([InlineKeyboardButton(t("admin_perms", lang), callback_data=f"admin:admins:perms:{admin.id}")])
        rows.append([InlineKeyboardButton(t("admin_delete", lang), callback_data=f"admin:admins:delete:{admin.id}")])
    rows.append([InlineKeyboardButton(t("back", lang), callback_data="admin:admins:list")])
    return InlineKeyboardMarkup(rows)


def admin_permissions_keyboard(lang: str, admin: AdminView) -> InlineKeyboardMarkup:
    rows = []
    for perm in ALL_PERMISSIONS:
        mark = "\u2705" if perm in admin.permissions else "\u2b1c"
        rows.append([InlineKeyboardButton(f"{mark} {perm}", callback_data=f"admin:admins:permtoggle:{admin.id}:{perm}")])
    rows.append([InlineKeyboardButton(t("back", lang), callback_data=f"admin:admins:view:{admin.id}")])
    return InlineKeyboardMarkup(rows)


def role_choice_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(Role.ADMIN.value, callback_data=f"admin:admins:role:{Role.ADMIN.value}")],
            [InlineKeyboardButton(Role.MODERATOR.value, callback_data=f"admin:admins:role:{Role.MODERATOR.value}")],
        ]
    )


# ---------- Payment methods (admin CRUD) ----------

def payment_methods_root_keyboard(lang: str, methods: list[PaymentMethodView]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(t("method_add", lang), callback_data="admin:paymethods:add")]]
    for m in methods:
        mark = "" if m.enabled else " \U0001F6AB"
        rows.append(
            [InlineKeyboardButton(truncate(m.name) + mark, callback_data=f"admin:paymethods:view:{m.id}")]
        )
    rows.append([InlineKeyboardButton(t("back", lang), callback_data="admin:root")])
    return InlineKeyboardMarkup(rows)


def payment_method_manage_keyboard(lang: str, method: PaymentMethodView) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(t("method_rename", lang), callback_data=f"admin:paymethods:rename:{method.id}")]]
    if not method.is_builtin_stars:
        rows.append(
            [InlineKeyboardButton(t("method_edit_instructions", lang), callback_data=f"admin:paymethods:instructions:{method.id}")]
        )
    rows.append([InlineKeyboardButton(t("method_toggle", lang), callback_data=f"admin:paymethods:toggle:{method.id}")])
    if not method.is_builtin_stars:
        rows.append([InlineKeyboardButton(t("method_delete", lang), callback_data=f"admin:paymethods:delete:{method.id}")])
    rows.append([InlineKeyboardButton(t("back", lang), callback_data="admin:paymethods:root")])
    return InlineKeyboardMarkup(rows)


# ---------- Per-button payment method assignment ----------

def button_payment_methods_keyboard(
    lang: str, button_id: int, all_methods: list[PaymentMethodView], assigned_ids: set[int]
) -> InlineKeyboardMarkup:
    rows = []
    for m in all_methods:
        mark = "\u2705" if m.id in assigned_ids else "\u2b1c"
        rows.append(
            [InlineKeyboardButton(f"{mark} {m.name}", callback_data=f"admin:buttons:paymethodtoggle:{button_id}:{m.id}")]
        )
    rows.append([InlineKeyboardButton(t("back", lang), callback_data=f"admin:buttons:view:{button_id}")])
    return InlineKeyboardMarkup(rows)
