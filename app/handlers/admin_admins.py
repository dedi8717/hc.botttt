from __future__ import annotations

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.config import config
from app.handlers.admin import is_owner, require_permission
from app.utils.telegram_helpers import safe_edit_message_text
from app.keyboards.admin import (
    admin_permissions_keyboard,
    admin_view_keyboard,
    admins_list_keyboard,
    admins_panel_keyboard,
    role_choice_keyboard,
)
from app.services import admin_service, user_service
from app.states.admin_admins import AddAdminState
from app.utils.logger import log_admin_action
from app.utils.permissions import Permission, Role
from app.utils.translations import t

PERM = Permission.MANAGE_ADMINS.value


def _lang(update: Update) -> str:
    return user_service.get_language(update.effective_user.id) or "fa"


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    await update.message.reply_text(t("cancelled", lang))
    return ConversationHandler.END


async def admins_root(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    await safe_edit_message_text(query, t("admins_panel", lang), reply_markup=admins_panel_keyboard(lang))


async def admins_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    admins = admin_service.list_admins()
    await safe_edit_message_text(query, 
        t("admin_list", lang), reply_markup=admins_list_keyboard(lang, admins, config.OWNER_ID)
    )


async def admin_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    admin_id = int(query.data.split(":")[-1])
    admin = next((a for a in admin_service.list_admins() if a.id == admin_id), None)
    if not admin:
        await admins_list(update, context)
        return
    text = f"{admin.telegram_id}\n{admin.role}"
    await safe_edit_message_text(query, text, reply_markup=admin_view_keyboard(lang, admin, config.OWNER_ID))


async def admin_perms_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    admin_id = int(query.data.split(":")[-1])
    admin = next((a for a in admin_service.list_admins() if a.id == admin_id), None)
    if not admin or admin.telegram_id == config.OWNER_ID:
        return
    await safe_edit_message_text(query, t("admin_perms", lang), reply_markup=admin_permissions_keyboard(lang, admin))


async def admin_perm_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    parts = query.data.split(":")
    admin_id, perm = int(parts[-2]), parts[-1]

    admin = next((a for a in admin_service.list_admins() if a.id == admin_id), None)
    if not admin or admin.telegram_id == config.OWNER_ID:
        await query.answer()
        return

    # Only the owner may grant/revoke sensitive permissions (e.g. manage_admins).
    if perm == Permission.MANAGE_ADMINS.value and not is_owner(update.effective_user.id):
        await query.answer(text=t("no_permission", lang), show_alert=True)
        return

    granted = perm not in admin.permissions
    admin_service.set_permission(admin_id, perm, granted)
    await query.answer(text=t("success", lang))
    log_admin_action(update.effective_user.id, "toggle_admin_permission", f"admin_id={admin_id} perm={perm} granted={granted}")

    admin = next((a for a in admin_service.list_admins() if a.id == admin_id), None)
    await safe_edit_message_text(query, t("admin_perms", lang), reply_markup=admin_permissions_keyboard(lang, admin))


async def admin_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    admin_id = int(query.data.split(":")[-1])
    admin = next((a for a in admin_service.list_admins() if a.id == admin_id), None)
    if admin and admin.telegram_id == config.OWNER_ID:
        await query.answer(text=t("cannot_remove_owner", lang), show_alert=True)
        return
    admin_service.remove_admin(admin_id)
    await query.answer(text=t("admin_deleted", lang))
    log_admin_action(update.effective_user.id, "delete_admin", f"admin_id={admin_id}")
    await admins_list(update, context)


# ---------- Add admin (ConversationHandler) ----------

async def add_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return ConversationHandler.END
    lang = _lang(update)
    await safe_edit_message_text(query, t("ask_admin_id", lang))
    return AddAdminState.WAIT_ID


async def add_admin_receive_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    raw = update.message.text.strip()
    if not raw.lstrip("-").isdigit():
        await update.message.reply_text(t("invalid_id", lang))
        return AddAdminState.WAIT_ID
    context.user_data["new_admin_telegram_id"] = int(raw)
    await update.message.reply_text(t("choose_role", lang), reply_markup=role_choice_keyboard())
    return AddAdminState.CHOOSE_ROLE


async def add_admin_choose_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = _lang(update)
    role = query.data.split(":")[-1]
    if role not in (Role.ADMIN.value, Role.MODERATOR.value):
        return ConversationHandler.END

    telegram_id = context.user_data.pop("new_admin_telegram_id", None)
    if telegram_id is None:
        return ConversationHandler.END

    admin_service.add_admin(telegram_id, role, added_by=update.effective_user.id)
    log_admin_action(update.effective_user.id, "add_admin", f"new_admin_id={telegram_id} role={role}")
    await safe_edit_message_text(query, t("admin_added", lang))
    await query.message.reply_text(t("admins_panel", lang), reply_markup=admins_panel_keyboard(lang))
    return ConversationHandler.END


add_admin_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_admin_start, pattern=r"^admin:admins:add$")],
    states={
        AddAdminState.WAIT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_admin_receive_id)],
        AddAdminState.CHOOSE_ROLE: [
            CallbackQueryHandler(add_admin_choose_role, pattern=r"^admin:admins:role:\w+$")
        ],
    },
    fallbacks=[MessageHandler(filters.Regex("^/cancel$"), cancel_conversation)],
    name="add_admin_conversation",
    persistent=False,
)


def register(application) -> None:
    application.add_handler(CallbackQueryHandler(admins_root, pattern=r"^admin:admins:root$"))
    application.add_handler(CallbackQueryHandler(admins_list, pattern=r"^admin:admins:list$"))
    application.add_handler(CallbackQueryHandler(admin_view, pattern=r"^admin:admins:view:\d+$"))
    application.add_handler(CallbackQueryHandler(admin_perms_view, pattern=r"^admin:admins:perms:\d+$"))
    application.add_handler(
        CallbackQueryHandler(admin_perm_toggle, pattern=r"^admin:admins:permtoggle:\d+:\w+$")
    )
    application.add_handler(CallbackQueryHandler(admin_delete, pattern=r"^admin:admins:delete:\d+$"))
    application.add_handler(add_admin_conversation)
