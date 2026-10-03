from __future__ import annotations

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from app.keyboards.common import channel_join_keyboard
from app.services import admin_service, membership_service, user_service
from app.utils.translations import t


def _lang(update: Update) -> str:
    return user_service.get_language(update.effective_user.id) or "fa"


def _is_admin(telegram_id: int) -> bool:
    from app.handlers.admin import is_owner

    return is_owner(telegram_id) or admin_service.get_admin(telegram_id) is not None


async def send_join_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str) -> None:
    link = membership_service.channel_join_link()
    await context.bot.send_message(
        update.effective_chat.id, t("must_join_channel", lang), reply_markup=channel_join_keyboard(lang, link)
    )


async def require_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Returns True if the user may proceed (feature disabled, user is an
    admin, or membership confirmed). Otherwise sends the join prompt and
    returns False."""
    tg_id = update.effective_user.id
    if not membership_service.membership_required() or _is_admin(tg_id):
        return True

    if await membership_service.is_member(context.bot, tg_id):
        return True

    await send_join_prompt(update, context, _lang(update))
    return False


async def check_membership_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """callback_data: checkmembership"""
    query = update.callback_query
    tg_id = update.effective_user.id
    lang = _lang(update)

    if not membership_service.membership_required() or _is_admin(tg_id) or await membership_service.is_member(
        context.bot, tg_id
    ):
        await query.answer()
        from app.handlers.start import proceed_after_membership

        await proceed_after_membership(update, context)
        return

    await query.answer(text=t("still_not_member", lang), show_alert=True)


def register(application) -> None:
    application.add_handler(CallbackQueryHandler(check_membership_callback, pattern=r"^checkmembership$"))
