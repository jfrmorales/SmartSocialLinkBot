import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    CallbackQueryHandler,
    filters
)
from dotenv import load_dotenv
import os

from db import create_database
from commands import menu, list_groups, add_group, remove_group, admin_help, button_handler, list_unauthorized_attempts
from handlers import process_message, handle_group_join

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(dotenv_path="config/.env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

if not BOT_TOKEN or not ADMIN_ID:
    raise ValueError("The bot token or admin ID are not defined in the .env file")

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
