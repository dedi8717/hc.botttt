"""
Central configuration for the bot.

All sensitive/environment-specific values are read from environment
variables (see .env.example). Nothing sensitive is hard-coded here.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load variables from a .env file if present. Real deployments can also
# just set real environment variables directly.
load_dotenv(BASE_DIR / ".env")


def _get_int_env(name: str, default: int | None = None) -> int | None:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        raise RuntimeError(f"Environment variable {name} must be an integer, got: {raw!r}")


class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    OWNER_ID: int | None = _get_int_env("OWNER_ID")
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'bot.db'}")
    DEFAULT_CURRENCY: str = os.getenv("DEFAULT_CURRENCY", "IRT")
    PORT: int = _get_int_env("PORT", 8080)

    # Optional mandatory-channel-membership gate. Leave REQUIRED_CHANNEL
    # empty to disable the feature entirely. Accepts either a public
    # channel username (e.g. "@mychannel") or a numeric chat id (e.g.
    # "-1001234567890", needed for private channels) - either way, the
    # bot must be an admin member of that channel for the membership
    # check to work at all (a Telegram API requirement, not a code
    # limitation). REQUIRED_CHANNEL_LINK is the URL shown to users on
    # the "Join" button - if left empty and REQUIRED_CHANNEL is a public
    # "@username", the link is derived automatically; for a private
    # channel (numeric id), set this explicitly to an invite link.
    REQUIRED_CHANNEL: str = os.getenv("REQUIRED_CHANNEL", "").strip()
    REQUIRED_CHANNEL_LINK: str = os.getenv("REQUIRED_CHANNEL_LINK", "").strip()

    LOCALES_DIR: Path = BASE_DIR / "app" / "locales"
    LOGS_DIR: Path = BASE_DIR / "logs"

    SUPPORTED_LANGUAGES = ("fa", "en")
    DEFAULT_LANGUAGE = "fa"

    @classmethod
    def validate(cls) -> None:
        missing = []
        if not cls.BOT_TOKEN:
            missing.append("BOT_TOKEN")
        if not cls.OWNER_ID:
            missing.append("OWNER_ID")
        if missing:
            raise RuntimeError(
                "Missing required environment variables: "
                + ", ".join(missing)
                + ". Copy .env.example to .env and fill them in."
            )


config = Config()
