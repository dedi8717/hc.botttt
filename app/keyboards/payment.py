from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.payment_method_service import PaymentMethodView
from app.utils.translations import t


def payment_method_choice_keyboard(button_id: int, methods: list[PaymentMethodView]) -> InlineKeyboardMarkup:
    """One row per available payment method for this button."""
    rows = [
        [InlineKeyboardButton(m.name, callback_data=f"paymethod:{m.id}:{button_id}")] for m in methods
    ]
    return InlineKeyboardMarkup(rows)


def admin_review_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("\u2705 \u062a\u0627\u06cc\u06cc\u062f / Approve", callback_data=f"payadmin:approve:{payment_id}"),
                InlineKeyboardButton("\u274c \u0631\u062f / Reject", callback_data=f"payadmin:reject:{payment_id}"),
            ]
        ]
    )
