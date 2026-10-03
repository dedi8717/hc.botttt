"""
Optional "must join our channel first" gate.

Disabled entirely unless REQUIRED_CHANNEL is set in the environment.
When enabled, `is_member` calls Telegram's getChatMember on the
configured channel - which only works if the bot itself is an admin
member of that channel (a Telegram API requirement).
"""
from __future__ import annotations

from telegram import Bot
from telegram.error import TelegramError

from app.config import config
from app.utils.logger import system_logger

NOT_MEMBER_STATUSES = {"left", "kicked"}


def membership_required() -> bool:
    return bool(config.REQUIRED_CHANNEL)


def channel_join_link() -> str:
    if config.REQUIRED_CHANNEL_LINK:
        return config.REQUIRED_CHANNEL_LINK
    if config.REQUIRED_CHANNEL.startswith("@"):
        return f"https://t.me/{config.REQUIRED_CHANNEL[1:]}"
    return ""  # private channel with no link configured - caller should handle this


async def is_member(bot: Bot, telegram_id: int) -> bool:
    if not membership_required():
        return True
    try:
        member = await bot.get_chat_member(config.REQUIRED_CHANNEL, telegram_id)
        return member.status not in NOT_MEMBER_STATUSES
    except TelegramError as exc:
        # Most commonly: the bot isn't an admin of the channel, or the
        # channel id/username is wrong. Fail closed (treat as "not a
        # member") but log loudly so the misconfiguration gets noticed.
        system_logger.error("Membership check failed for channel %s: %s", config.REQUIRED_CHANNEL, exc)
        return False
