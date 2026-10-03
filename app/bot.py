from __future__ import annotations

import html
import traceback

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from app.config import config
from app.database.database import init_db, session_scope
from app.database.repositories import admin_repo
from app.handlers import admin, admin_admins, admin_buttons, admin_content, admin_messaging, admin_payment_methods, admin_settings, language, membership, start, user_menu, user_payment
from app.services import payment_method_service
from app.utils.logger import error_logger, system_logger


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the exception (never crash the bot) and give the user a friendly message."""
    tb_string = "".join(traceback.format_exception(None, context.error, context.error.__traceback__))
    error_logger.error("Unhandled exception: %s\nUpdate: %s\n%s", context.error, update, tb_string)

    if isinstance(update, Update):
        chat = update.effective_chat
        if chat:
            try:
                await context.bot.send_message(chat.id, "⚠️ خطایی رخ داد. / An error occurred.")
            except Exception:
                pass


def build_application() -> Application:
    config.validate()
    init_db()

    with session_scope() as session:
        admin_repo.ensure_owner(session, config.OWNER_ID)

    payment_method_service.ensure_defaults()

    application = Application.builder().token(config.BOT_TOKEN).build()

    # --- User-facing handlers ---
    application.add_handler(CommandHandler("start", start.start))
    application.add_handler(CallbackQueryHandler(language.set_language, pattern=r"^lang:set:(fa|en)$"))
    membership.register(application)
    user_payment.register(application)

    # --- Admin panel entry points ---
    application.add_handler(CommandHandler("admin", admin.admin_command))
    application.add_handler(CallbackQueryHandler(admin.admin_root_callback, pattern=r"^admin:root$"))
    application.add_handler(CallbackQueryHandler(admin.admin_stats_callback, pattern=r"^admin:stats:root$"))
    application.add_handler(CallbackQueryHandler(admin.admin_users_callback, pattern=r"^admin:users:root$"))

    # --- Admin feature modules ---
    admin_buttons.register(application)
    admin_content.register(application)
    admin_admins.register(application)
    admin_settings.register(application)
    admin_messaging.register(application)
    admin_payment_methods.register(application)

    # --- Main menu text navigation (reply keyboard) ---
    # Registered LAST: any active admin ConversationHandler above should
    # get first chance at a user's plain-text message (e.g. while they're
    # typing a new button name). Only text that doesn't belong to an
    # active conversation reaches this generic menu-navigation handler.
    user_menu.register(application)

    application.add_error_handler(error_handler)

    system_logger.info("Application built successfully.")
    return application
