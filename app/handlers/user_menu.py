from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from app.handlers.language import send_language_prompt
from app.keyboards.user import locked_content_keyboard, menu_reply_keyboard
from app.services import admin_service, menu_service, payment_service, user_service
from app.utils.helpers import format_price
from app.utils.translations import t


def _lang(update: Update) -> str:
    return user_service.get_language(update.effective_user.id) or "fa"


def _is_admin(telegram_id: int) -> bool:
    from app.handlers.admin import is_owner

    return is_owner(telegram_id) or admin_service.get_admin(telegram_id) is not None


async def _send_content(update: Update, context: ContextTypes.DEFAULT_TYPE, content, lang: str) -> None:
    chat_id = update.effective_chat.id
    if content.content_type == "text":
        await context.bot.send_message(chat_id, content.text or "")
    elif content.content_type == "photo":
        await context.bot.send_photo(chat_id, content.file_id, caption=content.caption)
    elif content.content_type == "video":
        await context.bot.send_video(chat_id, content.file_id, caption=content.caption)
    elif content.content_type == "document":
        await context.bot.send_document(chat_id, content.file_id, caption=content.caption)


async def render_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, button_id: int | None) -> None:
    """Sends content (if any) for `button_id`, then its children as the
    persistent reply keyboard. `button_id=None` means the root menu."""
    lang = _lang(update)

    if button_id is not None:
        for content in menu_service.get_contents(button_id, lang):
            await _send_content(update, context, content, lang)

    children = menu_service.get_children(button_id, lang)
    context.user_data["current_menu_id"] = button_id

    if button_id is None:
        text = t("main_menu", lang)
    else:
        button = menu_service.get_button(button_id, lang)
        text = button.name if button else t("main_menu", lang)
        if not children and not menu_service.get_contents(button_id, lang):
            text = t("empty_menu", lang)

    keyboard = menu_reply_keyboard(
        children, at_root=(button_id is None), show_admin_button=_is_admin(update.effective_user.id), lang=lang
    )
    await context.bot.send_message(update.effective_chat.id, text, reply_markup=keyboard)


async def refresh_current_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Re-sends just the current level's keyboard (no content) - used after
    a successful payment so lock icons update immediately."""
    lang = _lang(update)
    button_id = context.user_data.get("current_menu_id")
    children = menu_service.get_children(button_id, lang)
    if button_id is None:
        text = t("main_menu", lang)
    else:
        button = menu_service.get_button(button_id, lang)
        text = button.name if button else t("main_menu", lang)
    keyboard = menu_reply_keyboard(
        children, at_root=(button_id is None), show_admin_button=_is_admin(update.effective_user.id), lang=lang
    )
    await context.bot.send_message(update.effective_chat.id, text, reply_markup=keyboard)


async def handle_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_id = update.effective_user.id
    lang = user_service.get_language(tg_id)
    if lang is None:
        return  # user hasn't picked a language yet - let the language flow handle it

    from app.handlers.membership import require_membership

    if not await require_membership(update, context):
        return

    text = (update.message.text or "").strip()

    if text == t("change_language", lang):
        await send_language_prompt(update, context, lang)
        return

    if text == t("admin_panel", lang) and _is_admin(tg_id):
        from app.handlers.admin import show_admin_panel

        await show_admin_panel(update, context)
        return

    current_id = context.user_data.get("current_menu_id")

    if text == t("back", lang):
        parent_id = menu_service.build_breadcrumb_root(current_id) if current_id is not None else None
        await render_menu(update, context, parent_id)
        return

    children = menu_service.get_children(current_id, lang)
    matched = None
    for b in children:
        label = b.name if b.is_free else f"\U0001F512 {b.name}"
        if label == text:
            matched = b
            break

    if matched is None:
        # Unrecognized text (stale keyboard, random input, etc.) - recover
        # by just re-showing the current level.
        await render_menu(update, context, current_id)
        return

    if not matched.is_free and not payment_service.user_has_access(tg_id, matched.id):
        await context.bot.send_message(
            update.effective_chat.id,
            t("locked_content", lang, price=format_price(matched.price)),
            reply_markup=locked_content_keyboard(matched.id, lang),
        )
        return

    await render_menu(update, context, matched.id)


def register(application) -> None:
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_text))
