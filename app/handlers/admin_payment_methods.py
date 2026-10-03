"""
Admin CRUD for payment methods: create custom methods (card transfer,
crypto, etc.), edit their name/instructions, enable/disable, and delete.
The built-in Stars method is seeded automatically at startup and can be
renamed/toggled but never deleted, and has no editable instructions
(its "instructions" - the invoice - is generated in code).
"""
from __future__ import annotations

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.handlers.admin import require_permission
from app.keyboards.admin import payment_method_manage_keyboard, payment_methods_root_keyboard
from app.keyboards.common import confirm_cancel_keyboard
from app.services import payment_method_service, user_service
from app.states.admin_payment_methods import AddMethodState, InstructionsState, RenameMethodState
from app.utils.logger import log_admin_action
from app.utils.permissions import Permission
from app.utils.telegram_helpers import safe_edit_message_text
from app.utils.translations import t

PERM = Permission.MANAGE_PAYMENTS.value


def _lang(update: Update) -> str:
    return user_service.get_language(update.effective_user.id) or "fa"


def _manage_text(lang: str, method) -> str:
    text = t("method_manage_title", lang, name=method.name)
    if method.is_builtin_stars:
        text += f"\n\n{t('method_builtin_notice', lang)}"
    return text


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    await update.message.reply_text(t("cancelled", lang))
    return ConversationHandler.END


# ---------- Root list ----------

async def methods_root(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    methods = payment_method_service.list_all(lang)
    text = t("payment_methods_title", lang) if methods else t("no_payment_methods_yet", lang)
    await safe_edit_message_text(query, text, reply_markup=payment_methods_root_keyboard(lang, methods))


async def method_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    method_id = int(query.data.split(":")[-1])
    method = payment_method_service.get(method_id, lang)
    if not method:
        await methods_root(update, context)
        return
    await safe_edit_message_text(query, _manage_text(lang, method), reply_markup=payment_method_manage_keyboard(lang, method))


# ---------- Add method (ConversationHandler) ----------

async def add_method_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return ConversationHandler.END
    lang = _lang(update)
    await safe_edit_message_text(query, t("ask_method_name_fa", lang))
    return AddMethodState.NAME_FA


async def add_method_name_fa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    context.user_data["new_method_name_fa"] = update.message.text.strip()
    await update.message.reply_text(t("ask_method_name_en", lang))
    return AddMethodState.NAME_EN


async def add_method_name_en(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    name_en = update.message.text.strip()
    name_fa = context.user_data.pop("new_method_name_fa")

    method_id = payment_method_service.create(name_fa, name_en)
    log_admin_action(update.effective_user.id, "create_payment_method", f"id={method_id} name_fa={name_fa}")
    await update.message.reply_text(t("method_created", lang))

    method = payment_method_service.get(method_id, lang)
    await update.message.reply_text(_manage_text(lang, method), reply_markup=payment_method_manage_keyboard(lang, method))
    return ConversationHandler.END


add_method_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_method_start, pattern=r"^admin:paymethods:add$")],
    states={
        AddMethodState.NAME_FA: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_method_name_fa)],
        AddMethodState.NAME_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_method_name_en)],
    },
    fallbacks=[MessageHandler(filters.Regex("^/cancel$"), cancel_conversation)],
    name="add_method_conversation",
    persistent=False,
)


# ---------- Rename method (ConversationHandler) ----------

async def rename_method_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return ConversationHandler.END
    lang = _lang(update)
    method_id = int(query.data.split(":")[-1])
    context.user_data["rename_method_id"] = method_id
    await safe_edit_message_text(query, t("ask_method_name_fa", lang))
    return RenameMethodState.NAME_FA


async def rename_method_name_fa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    context.user_data["rename_method_name_fa"] = update.message.text.strip()
    await update.message.reply_text(t("ask_method_name_en", lang))
    return RenameMethodState.NAME_EN


async def rename_method_name_en(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    name_en = update.message.text.strip()
    method_id = context.user_data.pop("rename_method_id")
    name_fa = context.user_data.pop("rename_method_name_fa")

    payment_method_service.rename(method_id, name_fa, name_en)
    log_admin_action(update.effective_user.id, "rename_payment_method", f"id={method_id}")
    await update.message.reply_text(t("success", lang))

    method = payment_method_service.get(method_id, lang)
    await update.message.reply_text(_manage_text(lang, method), reply_markup=payment_method_manage_keyboard(lang, method))
    return ConversationHandler.END


rename_method_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(rename_method_start, pattern=r"^admin:paymethods:rename:\d+$")],
    states={
        RenameMethodState.NAME_FA: [MessageHandler(filters.TEXT & ~filters.COMMAND, rename_method_name_fa)],
        RenameMethodState.NAME_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, rename_method_name_en)],
    },
    fallbacks=[MessageHandler(filters.Regex("^/cancel$"), cancel_conversation)],
    name="rename_method_conversation",
    persistent=False,
)


# ---------- Edit instructions (ConversationHandler) ----------

async def instructions_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return ConversationHandler.END
    lang = _lang(update)
    method_id = int(query.data.split(":")[-1])
    context.user_data["instructions_method_id"] = method_id
    await safe_edit_message_text(query, t("ask_method_instructions_fa", lang))
    return InstructionsState.INSTRUCTIONS_FA


async def instructions_fa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    context.user_data["new_instructions_fa"] = update.message.text.strip()
    await update.message.reply_text(t("ask_method_instructions_en", lang))
    return InstructionsState.INSTRUCTIONS_EN


async def instructions_en(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    text_en = update.message.text.strip()
    method_id = context.user_data.pop("instructions_method_id")
    text_fa = context.user_data.pop("new_instructions_fa")

    payment_method_service.update_instructions(method_id, text_fa, text_en)
    log_admin_action(update.effective_user.id, "update_payment_method_instructions", f"id={method_id}")
    await update.message.reply_text(t("instructions_saved", lang))

    method = payment_method_service.get(method_id, lang)
    await update.message.reply_text(_manage_text(lang, method), reply_markup=payment_method_manage_keyboard(lang, method))
    return ConversationHandler.END


instructions_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(instructions_start, pattern=r"^admin:paymethods:instructions:\d+$")],
    states={
        InstructionsState.INSTRUCTIONS_FA: [MessageHandler(filters.TEXT & ~filters.COMMAND, instructions_fa)],
        InstructionsState.INSTRUCTIONS_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, instructions_en)],
    },
    fallbacks=[MessageHandler(filters.Regex("^/cancel$"), cancel_conversation)],
    name="method_instructions_conversation",
    persistent=False,
)


# ---------- Toggle / Delete (one-shot callbacks) ----------

async def toggle_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    method_id = int(query.data.split(":")[-1])
    payment_method_service.toggle_enabled(method_id)
    await query.answer(text=t("success", lang))
    log_admin_action(update.effective_user.id, "toggle_payment_method", f"id={method_id}")

    method = payment_method_service.get(method_id, lang)
    await safe_edit_message_text(query, _manage_text(lang, method), reply_markup=payment_method_manage_keyboard(lang, method))


async def delete_method_confirm_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    method_id = int(query.data.split(":")[-1])
    method = payment_method_service.get(method_id, lang)
    if method and method.is_builtin_stars:
        await query.answer(text=t("cannot_delete_builtin", lang), show_alert=True)
        return
    await safe_edit_message_text(
        query,
        t("confirm_delete_method", lang),
        reply_markup=confirm_cancel_keyboard(
            lang, f"admin:paymethods:delconfirm:{method_id}", f"admin:paymethods:view:{method_id}"
        ),
    )


async def delete_method_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    method_id = int(query.data.split(":")[-1])
    deleted = payment_method_service.delete(method_id)
    if not deleted:
        await query.answer(text=t("cannot_delete_builtin", lang), show_alert=True)
        return
    await query.answer(text=t("method_deleted", lang))
    log_admin_action(update.effective_user.id, "delete_payment_method", f"id={method_id}")

    methods = payment_method_service.list_all(lang)
    text = t("payment_methods_title", lang) if methods else t("no_payment_methods_yet", lang)
    await safe_edit_message_text(query, text, reply_markup=payment_methods_root_keyboard(lang, methods))


def register(application) -> None:
    application.add_handler(CallbackQueryHandler(methods_root, pattern=r"^admin:paymethods:root$"))
    application.add_handler(CallbackQueryHandler(method_view, pattern=r"^admin:paymethods:view:\d+$"))
    application.add_handler(add_method_conversation)
    application.add_handler(rename_method_conversation)
    application.add_handler(instructions_conversation)
    application.add_handler(CallbackQueryHandler(toggle_method, pattern=r"^admin:paymethods:toggle:\d+$"))
    application.add_handler(
        CallbackQueryHandler(delete_method_confirm_prompt, pattern=r"^admin:paymethods:delete:\d+$")
    )
    application.add_handler(
        CallbackQueryHandler(delete_method_confirm, pattern=r"^admin:paymethods:delconfirm:\d+$")
    )
