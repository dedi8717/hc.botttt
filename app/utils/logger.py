"""
Central logging configuration.

Creates three rotating log files under logs/:
    logs/errors.log   - unhandled errors / exceptions
    logs/admin.log     - admin actions (button/content/admin management)
    logs/system.log    - general system/startup events

Never logs secrets (BOT_TOKEN, etc). Stack traces only go to the log
files, never to the end user.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from app.config import config

config.LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _make_logger(name: str, filename: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger  # already configured (avoid duplicate handlers on reload)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = RotatingFileHandler(
        config.LOGS_DIR / filename, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


error_logger = _make_logger("bot.errors", "errors.log")
admin_logger = _make_logger("bot.admin", "admin.log")
system_logger = _make_logger("bot.system", "system.log")


def log_admin_action(telegram_id: int, action: str, details: str = "") -> None:
    admin_logger.info("admin_id=%s action=%s %s", telegram_id, action, details)
