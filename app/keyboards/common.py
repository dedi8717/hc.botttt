from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.utils.translations import t


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang:set:fa")],
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang:set:en")],
        ]
    )


def confirm_cancel_keyboard(lang: str, confirm_cb: str, cancel_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(t("confirm_yes_delete", lang), callback_data=confirm_cb)],
            [InlineKeyboardButton(t("confirm_no", lang), callback_data=cancel_cb)],
        ]
    )


def back_keyboard(lang: str, callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(t("back", lang), callback_data=callback_data)]])


def channel_join_keyboard(lang: str, join_link: str) -> InlineKeyboardMarkup:
    rows = []
    if join_link:
        rows.append([InlineKeyboardButton(t("join_channel_button", lang), url=join_link)])
    rows.append([InlineKeyboardButton(t("check_membership_button", lang), callback_data="checkmembership")])
    return InlineKeyboardMarkup(rows)
