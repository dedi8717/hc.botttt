"""
Admin -> user messaging: a direct message to one user, or a broadcast
to everyone who has ever started the bot. Both use `copy_message` so
any content type the admin sends (text, photo, video, document, etc.)
is relayed as-is without needing per-type branching.
"""
from __future__ import annotations

import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.database.database import session_scope
from app.database.repositories import user_repo
from app.handlers.admin import require_permission
from app.services import user_service
from app.states.admin_messaging import BroadcastState, DirectMessageState
from app.utils.logger import log_admin_action
from app.utils.permissions import Permission
from app.utils.telegram_helpers import safe_edit_message_text
from app.utils.translations import t

PERM = Permission.MANAGE_USERS.value


def _lang(update: Update) -> str:
    return user_service.get_language(update.effective_user.id) or "fa"


def _message_panel_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(t("message_to_user", lang), callback_data="admin:message:direct")],
            [InlineKeyboardButton(t("message_broadcast", lang), callback_data="admin:message:broadcast")],
            [InlineKeyboardButton(t("back", lang), callback_data="admin:root")],
        ]
    )


async def message_root(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    await safe_edit_message_text(query, t("message_panel_title", lang), reply_markup=_message_panel_keyboard(lang))


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    context.user_data.pop("direct_message_target", None)
    context.user_data.pop("broadcast_chat_id", None)
    context.user_data.pop("broadcast_message_id", None)
    await update.message.reply_text(t("cancelled", lang))
    return ConversationHandler.END


# ---------- Direct message to a specific user ----------

async def direct_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return ConversationHandler.END
    lang = _lang(update)
    await safe_edit_message_text(query, t("ask_target_user_id", lang))
    return DirectMessageState.WAIT_USER_ID


async def direct_receive_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    raw = update.message.text.strip()
    if not raw.lstrip("-").isdigit():
        await update.message.reply_text(t("invalid_id", lang))
        return DirectMessageState.WAIT_USER_ID

    target_id = int(raw)
    with session_scope() as session:
        user = user_repo.get_by_telegram_id(session, target_id)
    if not user:
        await update.message.reply_text(t("user_not_found", lang))
        return DirectMessageState.WAIT_USER_ID

    context.user_data["direct_message_target"] = target_id
    await update.message.reply_text(t("ask_message_content", lang))
    return DirectMessageState.WAIT_CONTENT


async def direct_receive_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    target_id = context.user_data.pop("direct_message_target", None)
    if target_id is None:
        return ConversationHandler.END

    try:
        await context.bot.copy_message(
            chat_id=target_id, from_chat_id=update.effective_chat.id, message_id=update.message.message_id
        )
        await update.message.reply_text(t("message_sent_success", lang))
        log_admin_action(update.effective_user.id, "send_direct_message", f"target={target_id}")
    except TelegramError:
        await update.message.reply_text(t("message_sent_failed", lang))

    return ConversationHandler.END


direct_message_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(direct_start, pattern=r"^admin:message:direct$")],
    states={
        DirectMessageState.WAIT_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, direct_receive_id)],
        DirectMessageState.WAIT_CONTENT: [
            MessageHandler(
                (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL) & ~filters.COMMAND,
                direct_receive_content,
            )
        ],
    },
    fallbacks=[MessageHandler(filters.Regex("^/cancel$"), cancel_conversation)],
    name="direct_message_conversation",
    persistent=False,
)


# ---------- Broadcast to all users ----------

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return ConversationHandler.END
    lang = _lang(update)
    await safe_edit_message_text(query, t("ask_broadcast_content", lang))
    return BroadcastState.WAIT_CONTENT


async def broadcast_receive_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    context.user_data["broadcast_chat_id"] = update.effective_chat.id
    context.user_data["broadcast_message_id"] = update.message.message_id

    with session_scope() as session:
        count = len(user_repo.get_all_telegram_ids(session))

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(t("confirm_yes_send", lang), callback_data="admin:message:broadcastconfirm")],
            [InlineKeyboardButton(t("confirm_no", lang), callback_data="admin:message:broadcastcancel")],
        ]
    )
    await update.message.reply_text(t("confirm_broadcast", lang, count=count), reply_markup=keyboard)
    return BroadcastState.CONFIRM


async def broadcast_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = _lang(update)

    chat_id = context.user_data.pop("broadcast_chat_id", None)
    message_id = context.user_data.pop("broadcast_message_id", None)
    if chat_id is None or message_id is None:
        return ConversationHandler.END

    await safe_edit_message_text(query, t("broadcast_started", lang))

    with session_scope() as session:
        targets = user_repo.get_all_telegram_ids(session)

    success, failed = 0, 0
    for target_id in targets:
        try:
            await context.bot.copy_message(chat_id=target_id, from_chat_id=chat_id, message_id=message_id)
            success += 1
        except TelegramError:
            failed += 1
        await asyncio.sleep(0.05)  # gentle pacing to stay under Telegram's rate limits

    log_admin_action(update.effective_user.id, "broadcast_message", f"success={success} failed={failed}")
    await context.bot.send_message(
        update.effective_chat.id, t("broadcast_finished", lang, success=success, failed=failed)
    )
    return ConversationHandler.END


async def broadcast_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = _lang(update)
    context.user_data.pop("broadcast_chat_id", None)
    context.user_data.pop("broadcast_message_id", None)
    await safe_edit_message_text(query, t("cancelled", lang))
    return ConversationHandler.END


broadcast_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(broadcast_start, pattern=r"^admin:message:broadcast$")],
    states={
        BroadcastState.WAIT_CONTENT: [
            MessageHandler(
                (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL) & ~filters.COMMAND,
                broadcast_receive_content,
            )
        ],
        BroadcastState.CONFIRM: [
            CallbackQueryHandler(broadcast_confirm, pattern=r"^admin:message:broadcastconfirm$"),
            CallbackQueryHandler(broadcast_cancel_callback, pattern=r"^admin:message:broadcastcancel$"),
        ],
    },
    fallbacks=[MessageHandler(filters.Regex("^/cancel$"), cancel_conversation)],
    name="broadcast_conversation",
    persistent=False,
)


def register(application) -> None:
    application.add_handler(CallbackQueryHandler(message_root, pattern=r"^admin:message:root$"))
    application.add_handler(direct_message_conversation)
    application.add_handler(broadcast_conversation)
