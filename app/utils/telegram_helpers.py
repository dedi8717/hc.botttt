"""
Small helpers for working with python-telegram-bot safely.
"""
from __future__ import annotations

from telegram.error import BadRequest


async def safe_edit_message_text(query, text: str, **kwargs) -> None:
    """
    Wraps query.edit_message_text and silently ignores Telegram's
    "Message is not modified" BadRequest, which happens whenever the new
    text+keyboard are byte-for-byte identical to what's already shown.
    That's a harmless no-op from the user's point of view, not a real
    error, so it should never surface as a crash or an error toast.
    """
    try:
        await query.edit_message_text(text, **kwargs)
    except BadRequest as exc:
        if "Message is not modified" not in str(exc):
            raise
