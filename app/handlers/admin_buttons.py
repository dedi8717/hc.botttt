from __future__ import annotations

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.database.repositories import button_repo
from app.database.database import session_scope
from app.handlers.admin import require_permission
from app.utils.telegram_helpers import safe_edit_message_text
from app.keyboards.admin import (
    button_manage_keyboard,
    button_parent_choice_keyboard,
    button_payment_methods_keyboard,
    buttons_root_keyboard,
)
from app.keyboards.common import confirm_cancel_keyboard
from app.services import menu_service, payment_method_service, user_service
from app.states.admin_buttons import AddButtonState, MoveParentState, PriceState, RenameButtonState
from app.utils.logger import log_admin_action
from app.utils.permissions import Permission
from app.utils.translations import t

PERM = Permission.MANAGE_BUTTONS.value


def _lang(update: Update) -> str:
    return user_service.get_language(update.effective_user.id) or "fa"


def _manage_title(lang: str, button) -> str:
    status = t("status_enabled", lang) if button.enabled else t("status_disabled", lang)
    return t("btn_manage_title", lang, name=button.name) + f"\n\n{status}"


# ---------- Root tree view ----------

async def buttons_root(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    children = menu_service.get_children(None, lang, only_enabled=False)
    text = t("admin_manage_buttons", lang) if children else t("no_buttons_yet", lang)
    await safe_edit_message_text(query, text, reply_markup=buttons_root_keyboard(lang, children))


async def button_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    button_id = int(query.data.split(":")[-1])
    button = menu_service.get_button(button_id, lang)
    if not button:
        await buttons_root(update, context)
        return
    await safe_edit_message_text(query, 
        _manage_title(lang, button), reply_markup=button_manage_keyboard(lang, button)
    )


# ---------- Add button (ConversationHandler) ----------

async def add_button_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return ConversationHandler.END
    lang = _lang(update)
    parent_id = int(query.data.split(":")[-1])
    context.user_data["new_button_parent_id"] = None if parent_id == 0 else parent_id
    await safe_edit_message_text(query, t("ask_name_fa", lang))
    return AddButtonState.NAME_FA


async def add_button_name_fa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    context.user_data["new_button_name_fa"] = update.message.text.strip()
    await update.message.reply_text(t("ask_name_en", lang))
    return AddButtonState.NAME_EN


async def add_button_name_en(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    context.user_data["new_button_name_en"] = update.message.text.strip()

    parent_id = context.user_data.get("new_button_parent_id")
    name_fa = context.user_data["new_button_name_fa"]
    name_en = context.user_data["new_button_name_en"]

    with session_scope() as session:
        button = button_repo.create(session, name_fa=name_fa, name_en=name_en, parent_id=parent_id)
        new_id = button.id

    log_admin_action(update.effective_user.id, "create_button", f"id={new_id} name_fa={name_fa}")
    await update.message.reply_text(t("button_created", lang))

    button = menu_service.get_button(new_id, lang)
    await update.message.reply_text(
        _manage_title(lang, button), reply_markup=button_manage_keyboard(lang, button)
    )
    context.user_data.pop("new_button_parent_id", None)
    context.user_data.pop("new_button_name_fa", None)
    context.user_data.pop("new_button_name_en", None)
    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    await update.message.reply_text(t("cancelled", lang))
    return ConversationHandler.END


add_button_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_button_start, pattern=r"^admin:buttons:add:\d+$")],
    states={
        AddButtonState.NAME_FA: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_button_name_fa)],
        AddButtonState.NAME_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_button_name_en)],
    },
    fallbacks=[MessageHandler(filters.Regex("^/cancel$"), cancel_conversation)],
    name="add_button_conversation",
    persistent=False,
)


# ---------- Rename button (ConversationHandler) ----------

async def rename_button_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return ConversationHandler.END
    lang = _lang(update)
    button_id = int(query.data.split(":")[-1])
    context.user_data["rename_button_id"] = button_id
    await safe_edit_message_text(query, t("ask_name_fa", lang))
    return RenameButtonState.NAME_FA


async def rename_button_name_fa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    context.user_data["rename_name_fa"] = update.message.text.strip()
    await update.message.reply_text(t("ask_name_en", lang))
    return RenameButtonState.NAME_EN


async def rename_button_name_en(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    name_en = update.message.text.strip()
    button_id = context.user_data.pop("rename_button_id")
    name_fa = context.user_data.pop("rename_name_fa")

    with session_scope() as session:
        button_repo.rename(session, button_id, name_fa, name_en)

    log_admin_action(update.effective_user.id, "rename_button", f"id={button_id}")
    await update.message.reply_text(t("success", lang))

    button = menu_service.get_button(button_id, lang)
    await update.message.reply_text(
        _manage_title(lang, button), reply_markup=button_manage_keyboard(lang, button)
    )
    return ConversationHandler.END


rename_button_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(rename_button_start, pattern=r"^admin:buttons:rename:\d+$")],
    states={
        RenameButtonState.NAME_FA: [MessageHandler(filters.TEXT & ~filters.COMMAND, rename_button_name_fa)],
        RenameButtonState.NAME_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, rename_button_name_en)],
    },
    fallbacks=[MessageHandler(filters.Regex("^/cancel$"), cancel_conversation)],
    name="rename_button_conversation",
    persistent=False,
)


# ---------- Price (ConversationHandler) ----------

async def price_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, Permission.MANAGE_PRICES.value):
        return ConversationHandler.END
    lang = _lang(update)
    button_id = int(query.data.split(":")[-1])
    context.user_data["price_button_id"] = button_id
    await safe_edit_message_text(query, t("ask_new_price", lang))
    return PriceState.AMOUNT


async def price_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    raw = update.message.text.strip().replace(",", "")
    if not raw.isdigit():
        await update.message.reply_text(t("invalid_price", lang))
        return PriceState.AMOUNT

    button_id = context.user_data.pop("price_button_id")
    with session_scope() as session:
        button_repo.set_price(session, button_id, int(raw))

    log_admin_action(update.effective_user.id, "set_price", f"id={button_id} price={raw}")
    await update.message.reply_text(t("price_set", lang))

    button = menu_service.get_button(button_id, lang)
    await update.message.reply_text(
        _manage_title(lang, button), reply_markup=button_manage_keyboard(lang, button)
    )
    return ConversationHandler.END


price_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(price_start, pattern=r"^admin:buttons:price:\d+$")],
    states={PriceState.AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, price_amount)]},
    fallbacks=[MessageHandler(filters.Regex("^/cancel$"), cancel_conversation)],
    name="price_conversation",
    persistent=False,
)


# ---------- Move to a different parent (ConversationHandler) ----------

async def move_parent_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return ConversationHandler.END
    lang = _lang(update)
    button_id = int(query.data.split(":")[-1])
    context.user_data["move_button_id"] = button_id
    with session_scope() as session:
        all_buttons = button_repo.get_all(session)
    candidates = [
        menu_service.get_button(b.id, lang)
        for b in all_buttons
        if b.id != button_id and not _is_descendant_local(all_buttons, button_id, b.id)
    ]
    prefix = "admin:buttons:setparent"
    await safe_edit_message_text(query, t("choose_parent", lang), reply_markup=button_parent_choice_keyboard(lang, candidates, prefix))
    return MoveParentState.CHOOSE_PARENT


def _is_descendant_local(all_buttons, ancestor_id: int, candidate_id: int) -> bool:
    by_parent = {}
    for b in all_buttons:
        by_parent.setdefault(b.parent_id, []).append(b.id)

    def walk(pid):
        for cid in by_parent.get(pid, []):
            if cid == candidate_id:
                return True
            if walk(cid):
                return True
        return False

    return walk(ancestor_id)


async def move_parent_choose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = _lang(update)
    new_parent_raw = int(query.data.split(":")[-1])
    new_parent_id = None if new_parent_raw == 0 else new_parent_raw
    button_id = context.user_data.pop("move_button_id", None)
    if button_id is None:
        return ConversationHandler.END

    with session_scope() as session:
        ok, reason = button_repo.move_to_parent(session, button_id, new_parent_id)

    if ok:
        log_admin_action(update.effective_user.id, "move_button", f"id={button_id} new_parent={new_parent_id}")
        await safe_edit_message_text(query, t("success", lang))
    else:
        await safe_edit_message_text(query, t("no_permission", lang) if reason == "not_found" else t("cancelled", lang))

    button = menu_service.get_button(button_id, lang)
    if button:
        await context.bot.send_message(
            update.effective_chat.id,
            _manage_title(lang, button),
            reply_markup=button_manage_keyboard(lang, button),
        )
    return ConversationHandler.END


move_parent_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(move_parent_start, pattern=r"^admin:buttons:moveparent:\d+$")],
    states={
        MoveParentState.CHOOSE_PARENT: [
            CallbackQueryHandler(move_parent_choose, pattern=r"^admin:buttons:setparent:\d+$")
        ]
    },
    fallbacks=[MessageHandler(filters.Regex("^/cancel$"), cancel_conversation)],
    name="move_parent_conversation",
    persistent=False,
)


# ---------- Simple one-shot callbacks (no conversation needed) ----------

async def toggle_free(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await require_permission(update, Permission.MANAGE_PRICES.value):
        return
    lang = _lang(update)
    button_id = int(query.data.split(":")[-1])
    with session_scope() as session:
        current = button_repo.get(session, button_id)
        new_free = not current.is_free if current else True
        button_repo.set_free(session, button_id, new_free)
    await query.answer(text=t("success", lang))
    log_admin_action(update.effective_user.id, "toggle_free", f"id={button_id} is_free={new_free}")

    button = menu_service.get_button(button_id, lang)
    await safe_edit_message_text(query, 
        _manage_title(lang, button), reply_markup=button_manage_keyboard(lang, button)
    )


async def toggle_enabled(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    button_id = int(query.data.split(":")[-1])
    with session_scope() as session:
        button_repo.toggle_enabled(session, button_id)
    await query.answer(text=t("success", lang))
    log_admin_action(update.effective_user.id, "toggle_enabled", f"id={button_id}")

    button = menu_service.get_button(button_id, lang)
    await safe_edit_message_text(query, 
        _manage_title(lang, button), reply_markup=button_manage_keyboard(lang, button)
    )


async def move_position(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    parts = query.data.split(":")
    button_id, direction = int(parts[-2]), parts[-1]
    with session_scope() as session:
        button_repo.move_position(session, button_id, direction)
    await query.answer()
    log_admin_action(update.effective_user.id, "move_button_position", f"id={button_id} dir={direction}")

    button = menu_service.get_button(button_id, lang)
    await safe_edit_message_text(query, 
        _manage_title(lang, button), reply_markup=button_manage_keyboard(lang, button)
    )


async def delete_button_confirm_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    button_id = int(query.data.split(":")[-1])
    await safe_edit_message_text(query, 
        t("confirm_delete_button", lang),
        reply_markup=confirm_cancel_keyboard(
            lang, f"admin:buttons:delconfirm:{button_id}", f"admin:buttons:view:{button_id}"
        ),
    )


async def delete_button_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await require_permission(update, PERM):
        return
    lang = _lang(update)
    button_id = int(query.data.split(":")[-1])
    with session_scope() as session:
        existing = button_repo.get(session, button_id)
        parent_id = existing.parent_id if existing else None
        button_repo.delete(session, button_id)
    await query.answer(text=t("button_deleted", lang))
    log_admin_action(update.effective_user.id, "delete_button", f"id={button_id}")

    if parent_id:
        button = menu_service.get_button(parent_id, lang)
        await safe_edit_message_text(query, 
            _manage_title(lang, button), reply_markup=button_manage_keyboard(lang, button)
        )
    else:
        children = menu_service.get_children(None, lang, only_enabled=False)
        text = t("admin_manage_buttons", lang) if children else t("no_buttons_yet", lang)
        await safe_edit_message_text(query, text, reply_markup=buttons_root_keyboard(lang, children))


async def button_payment_methods_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await require_permission(update, Permission.MANAGE_PAYMENTS.value):
        return
    lang = _lang(update)
    button_id = int(query.data.split(":")[-1])
    button = menu_service.get_button(button_id, lang)
    if not button:
        await buttons_root(update, context)
        return
    all_methods = payment_method_service.list_all(lang)
    assigned_ids = payment_method_service.assigned_method_ids(button_id)
    await safe_edit_message_text(
        query,
        t("button_methods_title", lang, name=button.name),
        reply_markup=button_payment_methods_keyboard(lang, button_id, all_methods, assigned_ids),
    )


async def button_payment_method_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await require_permission(update, Permission.MANAGE_PAYMENTS.value):
        return
    lang = _lang(update)
    parts = query.data.split(":")
    button_id, method_id = int(parts[-2]), int(parts[-1])
    payment_method_service.toggle_button_method(button_id, method_id)
    await query.answer(text=t("success", lang))
    log_admin_action(update.effective_user.id, "toggle_button_payment_method", f"button_id={button_id} method_id={method_id}")

    button = menu_service.get_button(button_id, lang)
    all_methods = payment_method_service.list_all(lang)
    assigned_ids = payment_method_service.assigned_method_ids(button_id)
    await safe_edit_message_text(
        query,
        t("button_methods_title", lang, name=button.name),
        reply_markup=button_payment_methods_keyboard(lang, button_id, all_methods, assigned_ids),
    )


def register(application) -> None:
    application.add_handler(CallbackQueryHandler(buttons_root, pattern=r"^admin:buttons:root$"))
    application.add_handler(CallbackQueryHandler(button_view, pattern=r"^admin:buttons:view:\d+$"))
    application.add_handler(add_button_conversation)
    application.add_handler(rename_button_conversation)
    application.add_handler(price_conversation)
    application.add_handler(move_parent_conversation)
    application.add_handler(CallbackQueryHandler(toggle_free, pattern=r"^admin:buttons:freetoggle:\d+$"))
    application.add_handler(CallbackQueryHandler(toggle_enabled, pattern=r"^admin:buttons:toggle:\d+$"))
    application.add_handler(CallbackQueryHandler(move_position, pattern=r"^admin:buttons:move:\d+:(up|down)$"))
    application.add_handler(
        CallbackQueryHandler(delete_button_confirm_prompt, pattern=r"^admin:buttons:delete:\d+$")
    )
    application.add_handler(
        CallbackQueryHandler(delete_button_confirm, pattern=r"^admin:buttons:delconfirm:\d+$")
    )
    application.add_handler(
        CallbackQueryHandler(button_payment_methods_view, pattern=r"^admin:buttons:paymethods:\d+$")
    )
    application.add_handler(
        CallbackQueryHandler(button_payment_method_toggle, pattern=r"^admin:buttons:paymethodtoggle:\d+:\d+$")
    )
