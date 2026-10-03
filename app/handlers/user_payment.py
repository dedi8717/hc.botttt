"""
Payment entry point: the user picks from whichever payment methods are
configured for that button (see `payment_method_service`). The built-in
Stars method is automatic (a real Telegram invoice); every other method
is a manual receipt-review flow.
"""
from __future__ import annotations

from telegram import LabeledPrice, Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from app.config import config
from app.database.database import session_scope
from app.database.repositories import admin_repo
from app.keyboards.payment import admin_review_keyboard, payment_method_choice_keyboard
from app.services import menu_service, payment_method_service, payment_service, settings_service, user_service
from app.states.payment import PayState
from app.utils.logger import log_admin_action, system_logger
from app.utils.permissions import Permission, admin_has_permission
from app.utils.telegram_helpers import safe_edit_message_text
from app.utils.translations import t


def _lang(update: Update) -> str:
    return user_service.get_language(update.effective_user.id) or "fa"


def _payment_reviewer_ids() -> list[int]:
    """Owner + every admin holding the manage_payments permission."""
    ids: set[int] = set()
    if config.OWNER_ID:
        ids.add(config.OWNER_ID)
    with session_scope() as session:
        for admin in admin_repo.list_all(session):
            if admin_has_permission(admin, Permission.MANAGE_PAYMENTS.value):
                ids.add(admin.telegram_id)
    return list(ids)


# ---------- Step 1: choose a payment method ----------

async def pay_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """callback_data: pay:<button_id> - shows whichever methods this button offers."""
    query = update.callback_query
    await query.answer()
    lang = _lang(update)
    button_id = int(query.data.split(":")[-1])

    methods = payment_method_service.methods_for_button(button_id, lang, only_enabled=True)
    if not methods:
        await safe_edit_message_text(query, t("method_no_methods_configured", lang))
        return

    await safe_edit_message_text(
        query, t("choose_payment_method", lang), reply_markup=payment_method_choice_keyboard(button_id, methods)
    )


async def method_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    """callback_data: paymethod:<method_id>:<button_id> - dispatches to
    the Stars invoice flow or the generic receipt flow."""
    query = update.callback_query
    lang = _lang(update)
    parts = query.data.split(":")
    method_id, button_id = int(parts[1]), int(parts[2])

    method = payment_method_service.get(method_id, lang)
    if not method:
        await query.answer()
        return ConversationHandler.END

    if method.is_builtin_stars:
        await query.answer()
        await _send_stars_invoice(update, context, button_id, lang)
        return ConversationHandler.END

    await query.answer()
    context.user_data["receipt_button_id"] = button_id
    context.user_data["receipt_method_id"] = method_id
    text = t("ask_receipt", lang)
    if method.instructions:
        text = f"{method.instructions}\n\n{text}"
    await safe_edit_message_text(query, text)
    return PayState.WAIT_RECEIPT


# ---------- Telegram Stars (automatic) ----------

async def _send_stars_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE, button_id: int, lang: str) -> None:
    button = menu_service.get_button(button_id, lang)
    if not button or button.is_free or button.price <= 0:
        return  # stale/edited button

    description = t("invoice_description", lang, name=button.name)
    recipient = settings_service.get_stars_recipient()
    if recipient:
        description += "\n\n" + t("stars_recipient_line", lang, recipient=recipient)

    try:
        await context.bot.send_invoice(
            chat_id=update.effective_chat.id,
            title=button.name,
            description=description,
            payload=f"button:{button_id}",
            provider_token="",  # must be empty for Telegram Stars (XTR)
            currency="XTR",
            prices=[LabeledPrice(label=button.name, amount=button.price)],
        )
    except Exception as exc:
        system_logger.error("Failed to send Stars invoice: %s", exc)
        await context.bot.send_message(update.effective_chat.id, t("invoice_send_failed", lang))


async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Must be answered within 10 seconds or Telegram cancels the payment."""
    query = update.pre_checkout_query
    lang = user_service.get_language(query.from_user.id) or "fa"

    try:
        button_id = int(query.invoice_payload.split(":")[1])
    except (IndexError, ValueError):
        await query.answer(ok=False, error_message=t("invoice_send_failed", lang))
        return

    button = menu_service.get_button(button_id, lang)
    if not button or button.is_free or button.price != query.total_amount:
        await query.answer(ok=False, error_message=t("invoice_send_failed", lang))
        return

    await query.answer(ok=True)


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    info = update.message.successful_payment
    lang = _lang(update)

    try:
        button_id = int(info.invoice_payload.split(":")[1])
    except (IndexError, ValueError):
        return

    payment_service.record_successful_stars_payment(
        telegram_id=update.effective_user.id,
        button_id=button_id,
        amount=info.total_amount,
        telegram_charge_id=info.telegram_payment_charge_id,
    )
    log_admin_action(
        update.effective_user.id, "stars_payment_success", f"button_id={button_id} amount={info.total_amount}"
    )
    await update.message.reply_text(t("payment_successful", lang))

    from app.handlers.user_menu import refresh_current_keyboard

    await refresh_current_keyboard(update, context)

    if config.OWNER_ID:
        button = menu_service.get_button(button_id, lang)
        try:
            await context.bot.send_message(
                config.OWNER_ID,
                f"\U0001F31F +{info.total_amount} Stars\n{button.name if button else button_id}",
            )
        except Exception:
            pass


# ---------- Any custom method (manual receipt review) ----------

async def receive_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    msg = update.message

    if not msg.photo:
        await msg.reply_text(t("receipt_invalid", lang))
        return PayState.WAIT_RECEIPT

    button_id = context.user_data.pop("receipt_button_id", None)
    method_id = context.user_data.pop("receipt_method_id", None)
    if button_id is None or method_id is None:
        return ConversationHandler.END

    button = menu_service.get_button(button_id, lang)
    if not button:
        await msg.reply_text(t("cancelled", lang))
        return ConversationHandler.END

    receipt_file_id = msg.photo[-1].file_id
    payment_id = payment_service.create_pending_method_payment(
        update.effective_user.id, button_id, button.price, method_id, receipt_file_id
    )
    if payment_id is None:
        await msg.reply_text(t("cancelled", lang))
        return ConversationHandler.END

    await msg.reply_text(t("receipt_sent_to_admin", lang))
    log_admin_action(
        update.effective_user.id,
        "submit_payment_receipt",
        f"payment_id={payment_id} button_id={button_id} method_id={method_id}",
    )

    details = payment_service.get_payment_details(payment_id)
    button_name = details["button_name_fa"] if lang == "fa" else details["button_name_en"]
    method_name = (details["method_name_fa"] if lang == "fa" else details["method_name_en"]) or "?"
    caption = t(
        "admin_receipt_caption",
        lang,
        user=details["user_display"],
        method=method_name,
        button=button_name,
        price=details["amount"],
    )

    for reviewer_id in _payment_reviewer_ids():
        try:
            await context.bot.send_photo(
                reviewer_id, receipt_file_id, caption=caption, reply_markup=admin_review_keyboard(payment_id)
            )
        except Exception:
            continue  # e.g. reviewer never started a chat with the bot

    return ConversationHandler.END


async def receipt_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(update)
    context.user_data.pop("receipt_button_id", None)
    context.user_data.pop("receipt_method_id", None)
    await update.message.reply_text(t("cancelled", lang))
    return ConversationHandler.END


payment_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(method_selected, pattern=r"^paymethod:\d+:\d+$")],
    states={
        PayState.WAIT_RECEIPT: [MessageHandler(filters.PHOTO & ~filters.COMMAND, receive_receipt)],
    },
    fallbacks=[MessageHandler(filters.Regex("^/cancel$"), receipt_cancel)],
    name="payment_receipt_conversation",
    persistent=False,
)


async def _is_payment_reviewer(telegram_id: int) -> bool:
    if telegram_id == config.OWNER_ID:
        return True
    with session_scope() as session:
        admin = admin_repo.get_by_telegram_id(session, telegram_id)
        return admin_has_permission(admin, Permission.MANAGE_PAYMENTS.value)


async def admin_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """callback_data: payadmin:approve:<payment_id> | payadmin:reject:<payment_id>"""
    query = update.callback_query
    reviewer_id = update.effective_user.id
    lang = _lang(update)

    if not await _is_payment_reviewer(reviewer_id):
        await query.answer(text=t("no_permission", lang), show_alert=True)
        return

    parts = query.data.split(":")
    action, payment_id = parts[1], int(parts[2])

    if action == "approve":
        result = payment_service.approve_payment(payment_id)
        outcome_key, mark = "payment_approved", "\u2705"
    else:
        result = payment_service.reject_payment(payment_id)
        outcome_key, mark = "payment_rejected", "\u274c"

    if result is None:
        await query.answer(text=t("payment_already_reviewed", lang), show_alert=True)
        return

    await query.answer(text=t("success", lang))
    log_admin_action(reviewer_id, f"{action}_payment", f"payment_id={payment_id}")

    target_telegram_id = result.get("user_telegram_id")
    if target_telegram_id:
        user_lang = user_service.get_language(target_telegram_id) or "fa"
        try:
            await context.bot.send_message(target_telegram_id, t(outcome_key, user_lang))
        except Exception:
            pass

    try:
        current_caption = query.message.caption or ""
        await query.edit_message_caption(caption=f"{current_caption}\n\n{mark}")
    except Exception:
        pass


def register(application) -> None:
    application.add_handler(CallbackQueryHandler(pay_choice, pattern=r"^pay:\d+$"))
    application.add_handler(payment_conversation)
    application.add_handler(CallbackQueryHandler(admin_review, pattern=r"^payadmin:(approve|reject):\d+$"))
    application.add_handler(PreCheckoutQueryHandler(precheckout))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
