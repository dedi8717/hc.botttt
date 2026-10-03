from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.handlers.admin import require_permission
from app.services import settings_service, user_service
from app.states.admin_settings import SettingsState
from app.utils.logger import log_admin_action
from app.utils.permissions import Permission
from app.utils.telegram_helpers import safe_edit_message_text
from app.utils.translations import t

PERM = Permission.MANAGE_PAYMENTS.value


def _lang(update: Update) -> str:
    return user_service.get_language(update.effective_user.id) or "fa"


def _settings_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(t("btn_set_stars_recipient", lang), callback_data="admin:settings:setrecipient")],
            [InlineKeyboardButton(t("back", lang), callback_data="admin:root")],
        ]
    )


def _settings_text(lang: str) -> str:
    recipient = settings_service.get_stars_recipient()
    line = t("stars_recipient_current", lang, value=recipient) if recipient else t("stars_recipient_not_set", lang)
    return f"{t('settings_title', lang)}\n\n{line}"


async def settings_root(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    await safe_edit_message_text(query, _settings_text(lang), reply_markup=_settings_keyboard(lang))


async def set_recipient_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return ConversationHandler.END
    lang = _lang(update)
    await safe_edit_message_text(query, t("ask_stars_recipient", lang))
    return SettingsState.ASK_STARS_RECIPIENT


async def set_recipient_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    value = update.message.text.strip()
    settings_service.set_stars_recipient(value)
    log_admin_action(update.effective_user.id, "set_stars_recipient", value)
    await update.message.reply_text(t("stars_recipient_saved", lang))
    await update.message.reply_text(_settings_text(lang), reply_markup=_settings_keyboard(lang))
    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    await update.message.reply_text(t("cancelled", lang))
    return ConversationHandler.END


set_recipient_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(set_recipient_start, pattern=r"^admin:settings:setrecipient$")],
    states={
        SettingsState.ASK_STARS_RECIPIENT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, set_recipient_receive)
        ],
    },
    fallbacks=[MessageHandler(filters.Regex("^/cancel$"), cancel_conversation)],
    name="set_recipient_conversation",
    persistent=False,
)


def register(application) -> None:
    application.add_handler(CallbackQueryHandler(settings_root, pattern=r"^admin:settings:root$"))
    application.add_handler(set_recipient_conversation)
