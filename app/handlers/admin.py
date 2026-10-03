from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.utils.telegram_helpers import safe_edit_message_text

from app.config import config
from app.keyboards.admin import admin_panel_keyboard
from app.services import admin_service, user_service
from app.utils.translations import t


def is_owner(telegram_id: int) -> bool:
    return config.OWNER_ID is not None and telegram_id == config.OWNER_ID


async def require_permission(update: Update, permission: str) -> bool:
    """Returns True if the current user may proceed. Sends a denial message/alert otherwise."""
    tg_id = update.effective_user.id
    lang = user_service.get_language(tg_id) or "fa"

    if is_owner(tg_id):
        return True

    admin = admin_service.get_admin(tg_id)
    if not admin or permission not in admin.permissions:
        if update.callback_query:
            await update.callback_query.answer(text=t("no_permission", lang), show_alert=True)
        else:
            await update.message.reply_text(t("no_permission", lang))
        return False
    return True


async def require_admin(update: Update) -> bool:
    """Any admin (any role) may proceed, regardless of specific permission."""
    tg_id = update.effective_user.id
    lang = user_service.get_language(tg_id) or "fa"
    if is_owner(tg_id) or admin_service.get_admin(tg_id):
        return True
    if update.callback_query:
        await update.callback_query.answer(text=t("not_admin", lang), show_alert=True)
    else:
        await update.message.reply_text(t("not_admin", lang))
    return False


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_admin(update):
        return
    await show_admin_panel(update, context)


async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_id = update.effective_user.id
    lang = user_service.get_language(tg_id) or "fa"
    owner = is_owner(tg_id)
    admin = admin_service.get_admin(tg_id)
    perms = set(admin.permissions) if admin else set()

    text = t("admin_panel", lang)
    keyboard = admin_panel_keyboard(lang, perms, owner)
    if update.callback_query:
        await safe_edit_message_text(update.callback_query, text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text, reply_markup=keyboard)


async def admin_root_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await require_admin(update):
        return
    await show_admin_panel(update, context)


async def admin_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app.database.database import session_scope
    from app.database.repositories import button_repo
    from app.keyboards.common import back_keyboard

    query = update.callback_query
    await query.answer()
    if not await require_permission(update, "view_statistics"):
        return
    lang = user_service.get_language(update.effective_user.id) or "fa"

    user_stats = user_service.stats()
    with session_scope() as session:
        total_buttons = len(button_repo.get_all(session))
    total_admins = len(admin_service.list_admins())

    text = t(
        "stats_text",
        lang,
        total_users=user_stats["total_users"],
        total_buttons=total_buttons,
        total_admins=total_admins,
    )
    await safe_edit_message_text(query, text, reply_markup=back_keyboard(lang, "admin:root"))


async def admin_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app.database.database import session_scope
    from app.database.repositories import user_repo
    from app.keyboards.common import back_keyboard

    query = update.callback_query
    await query.answer()
    if not await require_permission(update, "manage_users"):
        return
    lang = user_service.get_language(update.effective_user.id) or "fa"

    with session_scope() as session:
        users = user_repo.list_users(session, limit=20)

    if not users:
        text = t("users_list_title", lang)
    else:
        lines = [t("users_list_title", lang), ""]
        for u in users:
            name = u.username or u.first_name or str(u.telegram_id)
            mark = f" {t('user_blocked_mark', lang)}" if u.is_blocked else ""
            lines.append(f"\u2022 {name} ({u.telegram_id}){mark}")
        text = "\n".join(lines)

    await safe_edit_message_text(query, text, reply_markup=back_keyboard(lang, "admin:root"))
