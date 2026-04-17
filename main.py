"""
Unified entry point — starts Telegram bot + optional Flask web dashboard.
Combines the existing hook bot (boot_hook.py) with the rate card system.
"""
import logging
import os
import threading

from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    Updater,
)

import config
from ratecard.core import database as db
from ratecard.bot.handlers import register_ratecard_handlers

# Import existing hook bot handlers (do not modify boot_hook.py)
from boot_hook import (
    handle_add_hooks,
    handle_category,
    handle_end,
    handle_hook,
    handle_style,
    start as hook_start,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


def run_flask():
    """Start Flask web dashboard in a daemon thread."""
    try:
        from ratecard.web.app import create_app
        app = create_app()
        log.info(f"Web dashboard: http://{config.FLASK_HOST}:{config.FLASK_PORT}")
        app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=False, use_reloader=False)
    except Exception as e:
        log.warning(f"Flask startup failed: {e}")


def main():
    token = config.TELEGRAM_TOKEN
    if not token:
        raise RuntimeError("TELEGRAM_TOKEN environment variable not set.")

    # Initialize database
    db.init_db(config.DB_PATH)
    log.info(f"Database: {config.DB_PATH}")

    # Start Flask in background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Build Telegram bot
    updater = Updater(token=token, use_context=True)
    dp = updater.dispatcher

    # ── Existing hook bot handlers ──────────────────────────
    dp.add_handler(CommandHandler("hook", lambda u, c: hook_start(u, c)))  # /hook for legacy
    dp.add_handler(CallbackQueryHandler(handle_hook,      pattern=r"^hook$"))
    dp.add_handler(CallbackQueryHandler(handle_category,  pattern=r"^category_"))
    dp.add_handler(CallbackQueryHandler(handle_style,     pattern=r"^style_"))
    dp.add_handler(CallbackQueryHandler(handle_add_hooks, pattern=r"^add_"))
    dp.add_handler(CallbackQueryHandler(handle_end,       pattern=r"^end$"))

    # ── Rate card handlers ──────────────────────────────────
    register_ratecard_handlers(dp)

    log.info("Bot started. Press Ctrl+C to stop.")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
