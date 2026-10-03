from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.handlers.start import show_main_menu
from app.keyboards.common import language_keyboard
from app.services import user_service
from app.utils.translations import t


async def send_language_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    """Triggered when the user taps the '🌐 Change Language' reply-keyboard button."""
    await update.message.reply_text(t("choose_language", lang), reply_markup=language_keyboard())


async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Triggered by the inline fa/en buttons on the language-choice message."""
    query = update.callback_query
    lang = query.data.split(":")[-1]
    user_service.set_language(update.effective_user.id, lang)
    await query.answer(text=t("language_set", lang))
    await show_main_menu(update, context, lang)
