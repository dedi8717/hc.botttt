from __future__ import annotations

from app.bot import build_application
from app.utils.logger import system_logger


def main() -> None:
    application = build_application()
    system_logger.info("Starting bot with long polling...")
    application.run_polling(allowed_updates=["message", "callback_query", "pre_checkout_query"])


if __name__ == "__main__":
    main()
