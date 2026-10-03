"""
Generic bot settings, stored as key/value pairs (see Settings model).

Currently used for one thing: an admin-configurable, display-only
"Stars recipient" identifier shown to users before they pay. Telegram
Stars payments always credit the bot's own balance - there is no way
for the Bot API to route a payment to an arbitrary Telegram user - so
this value is purely informational for the buyer, and any actual
transfer to that person has to be done manually by whoever controls the
bot's Stars balance.
"""
from __future__ import annotations

from app.database.database import session_scope
from app.database.repositories import settings_repo

STARS_RECIPIENT_KEY = "stars_recipient"


def get_stars_recipient() -> str | None:
    with session_scope() as session:
        return settings_repo.get(session, STARS_RECIPIENT_KEY)


def set_stars_recipient(value: str) -> None:
    with session_scope() as session:
        settings_repo.set(session, STARS_RECIPIENT_KEY, value)
