import logging
from logging.handlers import TimedRotatingFileHandler
import os
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    CallbackQueryHandler,
    filters
)
from dotenv import load_dotenv

from db import create_database
from commands import menu, list_groups, add_group, remove_group, admin_help, button_handler, list_unauthorized_attempts
from handlers import process_message, handle_group_join

# Create logs directory if it doesn't exist
if not os.path.exists("logs"):
    os.makedirs("logs")

# Logging configuration
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Handler for logging to a file that rotates daily
file_handler = TimedRotatingFileHandler("logs/bot.log", when="midnight", interval=1, backupCount=7)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

# Handler for logging to the console
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

# Get the root logger and add the handlers
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Load environment variables
load_dotenv(dotenv_path="config/.env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not BOT_TOKEN or not ADMIN_ID:
    logger.error("The bot token or admin ID are not defined in the .env file")
    raise ValueError("The bot token or admin ID are not defined in the .env file")

try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    logger.error("ADMIN_ID is not a valid integer")
    raise ValueError("ADMIN_ID must be an integer")

def main():
    # Ensure the database is created or verified on startup
    create_database()

    # Create the bot application
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Set global bot data
    app.bot_data["admin_id"] = ADMIN_ID

    # Command handlers
    app.add_handler(CommandHandler("menu", menu))  # Interactive menu
    app.add_handler(CommandHandler("list_groups", list_groups))
    app.add_handler(CommandHandler("add_group", add_group))
    app.add_handler(CommandHandler("remove_group", remove_group))
    app.add_handler(CommandHandler("list_attempts", list_unauthorized_attempts))
    app.add_handler(CommandHandler("help", admin_help))

    # Menu button handlers
    app.add_handler(CallbackQueryHandler(button_handler))

    # Message handlers
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, process_message))

    # Handler for events when the bot is added to a group
    app.add_handler(ChatMemberHandler(handle_group_join, ChatMemberHandler.MY_CHAT_MEMBER))

    # Start the bot
    logger.info("Bot started and running...")
    app.run_polling()

if __name__ == "__main__":
    main()
