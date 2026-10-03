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
from app.utils.telegram_helpers import safe_edit_message_text
from app.keyboards.admin import (
    content_edit_field_keyboard,
    content_list_keyboard,
    content_root_keyboard,
    move_up_down_keyboard,
)
from app.keyboards.common import confirm_cancel_keyboard
from app.services import content_service, menu_service, user_service
from app.states.admin_content import AddContentState, EditContentState
from app.utils.logger import log_admin_action
from app.utils.permissions import Permission
from app.utils.translations import t

PERM = Permission.MANAGE_CONTENT.value


def _lang(update: Update) -> str:
    return user_service.get_language(update.effective_user.id) or "fa"


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    await update.message.reply_text(t("cancelled", lang))
    return ConversationHandler.END


# ---------- Content root menu ----------

async def content_root(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    button_id = int(query.data.split(":")[-1])
    button = menu_service.get_button(button_id, lang)
    contents = menu_service.get_contents(button_id, lang)
    text = t("content_manage_title", lang, name=button.name) if contents else t("no_content_yet", lang)
    await safe_edit_message_text(query, text, reply_markup=content_root_keyboard(lang, button_id, contents))


async def content_list_for_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """callback_data: admin:content:editlist:<btn> | dellist:<btn> | movelist:<btn>"""
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    parts = query.data.split(":")
    action_key, button_id = parts[2], int(parts[3])
    action_map = {"editlist": "editopen", "dellist": "delconfirm", "movelist": "move"}
    action = action_map[action_key]
    contents = menu_service.get_contents(button_id, lang)
    await safe_edit_message_text(query, 
        t("choose_content_to_edit", lang), reply_markup=content_list_keyboard(lang, button_id, contents, action)
    )


# ---------- Add content (ConversationHandler) ----------

async def add_content_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return ConversationHandler.END
    lang = _lang(update)
    button_id = int(query.data.split(":")[-1])
    context.user_data["content_button_id"] = button_id
    await safe_edit_message_text(query, t("ask_content", lang))
    return AddContentState.WAIT_CONTENT


async def add_content_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    msg = update.message
    button_id = context.user_data["content_button_id"]

    if msg.text:
        content_id = content_service.add_text(button_id, text_fa=msg.text, text_en=msg.text)
        context.user_data["new_content_id"] = content_id
        await update.message.reply_text(t("content_saved", lang))
        return await _finish_add_content(update, context)

    content_type, file_id = None, None
    if msg.photo:
        content_type, file_id = "photo", msg.photo[-1].file_id
    elif msg.video:
        content_type, file_id = "video", msg.video.file_id
    elif msg.document:
        content_type, file_id = "document", msg.document.file_id
    else:
        await update.message.reply_text(t("ask_content", lang))
        return AddContentState.WAIT_CONTENT

    content_id = content_service.add_media(button_id, content_type, file_id)
    context.user_data["new_content_id"] = content_id
    await update.message.reply_text(t("ask_caption_fa", lang))
    return AddContentState.CAPTION_FA


async def add_content_caption_fa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    content_id = context.user_data["new_content_id"]
    if update.message.text.strip() != "/skip":
        content_service.set_caption(content_id, "fa", update.message.text.strip())
    await update.message.reply_text(t("ask_caption_en", lang))
    return AddContentState.CAPTION_EN


async def add_content_caption_en(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    content_id = context.user_data["new_content_id"]
    if update.message.text.strip() != "/skip":
        content_service.set_caption(content_id, "en", update.message.text.strip())
    lang = _lang(update)
    await update.message.reply_text(t("content_saved", lang))
    return await _finish_add_content(update, context)


async def _finish_add_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    button_id = context.user_data.pop("content_button_id")
    context.user_data.pop("new_content_id", None)

    log_admin_action(update.effective_user.id, "add_content", f"button_id={button_id}")

    button = menu_service.get_button(button_id, lang)
    contents = menu_service.get_contents(button_id, lang)
    await update.message.reply_text(
        t("content_manage_title", lang, name=button.name),
        reply_markup=content_root_keyboard(lang, button_id, contents),
    )
    return ConversationHandler.END


add_content_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_content_start, pattern=r"^admin:content:add:\d+$")],
    states={
        AddContentState.WAIT_CONTENT: [
            MessageHandler(
                (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL) & ~filters.COMMAND,
                add_content_receive,
            )
        ],
        AddContentState.CAPTION_FA: [MessageHandler(filters.TEXT, add_content_caption_fa)],
        AddContentState.CAPTION_EN: [MessageHandler(filters.TEXT, add_content_caption_en)],
    },
    fallbacks=[MessageHandler(filters.Regex("^/cancel$"), cancel_conversation)],
    name="add_content_conversation",
    persistent=False,
)


# ---------- Edit content (ConversationHandler) ----------

async def edit_content_open(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return ConversationHandler.END
    lang = _lang(update)
    content_id = int(query.data.split(":")[-1])
    content = content_service.get(content_id)
    if not content:
        return ConversationHandler.END
    context.user_data["edit_content_id"] = content_id
    matches = [c for c in menu_service.get_contents(content.button_id, lang) if c.id == content_id]
    if not matches:
        return ConversationHandler.END
    await safe_edit_message_text(query, t("choose_edit_field", lang), reply_markup=content_edit_field_keyboard(lang, matches[0]))
    return EditContentState.CHOOSE_FIELD


async def edit_content_choose_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = _lang(update)
    parts = query.data.split(":")
    content_id, field = int(parts[-2]), parts[-1]
    context.user_data["edit_content_id"] = content_id
    context.user_data["edit_field"] = field

    if field == "text":
        await safe_edit_message_text(query, t("ask_new_text", lang))
        return EditContentState.NEW_TEXT
    if field == "media":
        await safe_edit_message_text(query, t("ask_new_media", lang))
        return EditContentState.NEW_MEDIA
    if field == "caption_fa":
        await safe_edit_message_text(query, t("ask_caption_fa", lang))
        return EditContentState.NEW_CAPTION_FA
    if field == "caption_en":
        await safe_edit_message_text(query, t("ask_caption_en", lang))
        return EditContentState.NEW_CAPTION_EN
    return ConversationHandler.END


async def edit_content_new_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    content_id = context.user_data.pop("edit_content_id")
    text = update.message.text.strip()
    content_service.update_text(content_id, text, text)
    return await _finish_edit(update, context, content_id)


async def edit_content_new_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    content_id = context.user_data.pop("edit_content_id")
    msg = update.message
    if msg.photo:
        content_service.update_media(content_id, msg.photo[-1].file_id, "photo")
    elif msg.video:
        content_service.update_media(content_id, msg.video.file_id, "video")
    elif msg.document:
        content_service.update_media(content_id, msg.document.file_id, "document")
    else:
        lang = _lang(update)
        await update.message.reply_text(t("ask_new_media", lang))
        context.user_data["edit_content_id"] = content_id
        return EditContentState.NEW_MEDIA
    return await _finish_edit(update, context, content_id)


async def edit_content_new_caption_fa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    content_id = context.user_data.pop("edit_content_id")
    content_service.set_caption(content_id, "fa", update.message.text.strip())
    return await _finish_edit(update, context, content_id)


async def edit_content_new_caption_en(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    content_id = context.user_data.pop("edit_content_id")
    content_service.set_caption(content_id, "en", update.message.text.strip())
    return await _finish_edit(update, context, content_id)


async def _finish_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, content_id: int) -> int:
    lang = _lang(update)
    context.user_data.pop("edit_field", None)
    content = content_service.get(content_id)
    log_admin_action(update.effective_user.id, "edit_content", f"content_id={content_id}")
    await update.message.reply_text(t("content_saved", lang))
    if content:
        button = menu_service.get_button(content.button_id, lang)
        contents = menu_service.get_contents(content.button_id, lang)
        await update.message.reply_text(
            t("content_manage_title", lang, name=button.name),
            reply_markup=content_root_keyboard(lang, content.button_id, contents),
        )
    return ConversationHandler.END


async def edit_content_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    return ConversationHandler.END


edit_content_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(edit_content_open, pattern=r"^admin:content:editopen:\d+$")],
    states={
        EditContentState.CHOOSE_FIELD: [
            CallbackQueryHandler(edit_content_choose_field, pattern=r"^admin:content:editfield:\d+:\w+$"),
            CallbackQueryHandler(edit_content_cancel, pattern=r"^admin:content:editcancel$"),
        ],
        EditContentState.NEW_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_content_new_text)],
        EditContentState.NEW_MEDIA: [
            MessageHandler(
                (filters.PHOTO | filters.VIDEO | filters.Document.ALL) & ~filters.COMMAND, edit_content_new_media
            )
        ],
        EditContentState.NEW_CAPTION_FA: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_content_new_caption_fa)
        ],
        EditContentState.NEW_CAPTION_EN: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_content_new_caption_en)
        ],
    },
    fallbacks=[MessageHandler(filters.Regex("^/cancel$"), cancel_conversation)],
    name="edit_content_conversation",
    persistent=False,
)


# ---------- Delete / move (one-shot callbacks) ----------

async def delete_content_confirm_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    content_id = int(query.data.split(":")[-1])
    content = content_service.get(content_id)
    await safe_edit_message_text(query, 
        t("confirm_delete_button", lang),
        reply_markup=confirm_cancel_keyboard(
            lang,
            f"admin:content:delfinal:{content_id}",
            f"admin:content:root:{content.button_id}" if content else "admin:buttons:root",
        ),
    )


async def delete_content_final(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    content_id = int(query.data.split(":")[-1])
    content = content_service.get(content_id)
    button_id = content.button_id if content else None
    content_service.delete(content_id)
    await query.answer(text=t("content_deleted", lang))
    log_admin_action(update.effective_user.id, "delete_content", f"content_id={content_id}")

    if button_id:
        button = menu_service.get_button(button_id, lang)
        contents = menu_service.get_contents(button_id, lang)
        text = t("content_manage_title", lang, name=button.name) if contents else t("no_content_yet", lang)
        await safe_edit_message_text(query, text, reply_markup=content_root_keyboard(lang, button_id, contents))


async def move_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    content_id = int(query.data.split(":")[-1])
    content = content_service.get(content_id)
    if not content:
        return
    await query.answer()
    await safe_edit_message_text(query, 
        t("choose_content_to_edit", lang), reply_markup=move_up_down_keyboard(lang, content_id, "admin:content:domove")
    )


async def do_move_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    parts = query.data.split(":")
    content_id, direction = int(parts[-2]), parts[-1]
    content_service.move(content_id, direction)
    await query.answer(text=t("success", lang))
    log_admin_action(update.effective_user.id, "move_content", f"content_id={content_id} dir={direction}")

    content = content_service.get(content_id)
    if content:
        button = menu_service.get_button(content.button_id, lang)
        contents = menu_service.get_contents(content.button_id, lang)
        await safe_edit_message_text(query, 
            t("content_manage_title", lang, name=button.name),
            reply_markup=content_root_keyboard(lang, content.button_id, contents),
        )


def register(application) -> None:
    application.add_handler(CallbackQueryHandler(content_root, pattern=r"^admin:content:root:\d+$"))
    application.add_handler(
        CallbackQueryHandler(content_list_for_action, pattern=r"^admin:content:(editlist|dellist|movelist):\d+$")
    )
    application.add_handler(add_content_conversation)
    application.add_handler(edit_content_conversation)
    application.add_handler(
        CallbackQueryHandler(delete_content_confirm_prompt, pattern=r"^admin:content:delconfirm:\d+$")
    )
    application.add_handler(CallbackQueryHandler(delete_content_final, pattern=r"^admin:content:delfinal:\d+$"))
    application.add_handler(CallbackQueryHandler(move_content, pattern=r"^admin:content:move:\d+$"))
    application.add_handler(CallbackQueryHandler(do_move_content, pattern=r"^admin:content:domove:\d+:(up|down)$"))
