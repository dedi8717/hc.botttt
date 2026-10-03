from __future__ import annotations

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.services.menu_service import ButtonView
from app.utils.translations import t


def menu_reply_keyboard(
    buttons: list[ButtonView], at_root: bool, show_admin_button: bool, lang: str
) -> ReplyKeyboardMarkup:
    """
    buttons: children of the menu currently shown.
    at_root: True if this is the top-level main menu (no Back row).
    show_admin_button: True to add a root-level "Admin Panel" row (admins only).
    """
    rows = [[KeyboardButton(b.name if b.is_free else f"\U0001F512 {b.name}")] for b in buttons]

    control_row = [KeyboardButton(t("change_language", lang))]
    if not at_root:
        control_row.append(KeyboardButton(t("back", lang)))
    rows.append(control_row)

    if at_root and show_admin_button:
        rows.append([KeyboardButton(t("admin_panel", lang))])

    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def locked_content_keyboard(button_id: int, lang: str) -> InlineKeyboardMarkup:
    """Inline Pay button only - navigation itself is handled by the
    persistent reply keyboard, which stays visible underneath this
    message, so no inline Back button is needed here."""
    return InlineKeyboardMarkup([[InlineKeyboardButton(t("pay_button", lang), callback_data=f"pay:{button_id}")]])
