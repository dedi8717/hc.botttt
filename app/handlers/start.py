from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.keyboards.common import language_keyboard
from app.keyboards.user import menu_reply_keyboard
from app.services import admin_service, menu_service, user_service
from app.utils.translations import t


def _is_admin(telegram_id: int) -> bool:
    from app.handlers.admin import is_owner

    return is_owner(telegram_id) or admin_service.get_admin(telegram_id) is not None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    user_service.register_or_update(tg_user.id, tg_user.username, tg_user.first_name)
    context.user_data["current_menu_id"] = None

    from app.handlers.membership import require_membership

    if not await require_membership(update, context):
        return

    await proceed_after_membership(update, context)


async def proceed_after_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows the language picker or the main menu, whichever applies.
    Message-agnostic (uses context.bot.send_message) so it works whether
    it's called from a command, a plain message, or a callback query."""
    tg_id = update.effective_user.id
    language = user_service.get_language(tg_id)
    if not language:
        await context.bot.send_message(
            update.effective_chat.id, t("choose_language", "fa"), reply_markup=language_keyboard()
        )
        return

    await show_main_menu(update, context, language)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    """Always sends a brand-new message - a persistent reply keyboard can
    only be attached/replaced by sending a message, it can't be 'edited'
    the way an inline keyboard can."""
    context.user_data["current_menu_id"] = None
    tg_id = update.effective_user.id
    buttons = menu_service.get_children(None, lang)
    keyboard = menu_reply_keyboard(buttons, at_root=True, show_admin_button=_is_admin(tg_id), lang=lang)
    await context.bot.send_message(update.effective_chat.id, t("main_menu", lang), reply_markup=keyboard)
