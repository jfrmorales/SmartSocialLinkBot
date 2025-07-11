from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.error import TelegramError
from db import get_all_groups, add_group as db_add_group, remove_group as db_remove_group, is_group_allowed, get_unauthorized_attempts
import logging
from functools import wraps

logger = logging.getLogger(__name__)

async def send_response(update: Update, text: str, reply_markup=None, parse_mode=None):
    """Helper function to send responses for both callback queries and regular messages."""
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

def validate_chat_id(chat_id: str) -> tuple[bool, str]:
    """Validates and normalizes a chat ID."""
    if not chat_id:
        return False, "Chat ID cannot be empty."
    
    chat_id = chat_id.strip()
    
    # Remove leading minus if present for validation
    clean_id = chat_id.replace("-", "")
    
    if not clean_id.isdigit():
        return False, "Invalid group ID format. Please provide a numeric ID."
    
    # Ensure it has the minus prefix for groups
    if not chat_id.startswith("-"):
        chat_id = f"-{chat_id}"
    
    return True, chat_id

def admin_only(func):
    """Decorator for commands and callbacks that only the admin can use."""
    @wraps(func)
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != context.bot_data["admin_id"]:
            if update.callback_query:
                await update.callback_query.answer("You do not have permission to use this option.", show_alert=True)
            else:
                await update.message.reply_text("You do not have permission to use this command.")
            logger.warning(f"Unauthorized user {user_id} attempted to use {func.__name__}")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

@admin_only
async def menu(update: Update, context: CallbackContext):
    """Displays the interactive menu for the admin."""
    keyboard = [
        [InlineKeyboardButton("List Groups", callback_data="list_groups")],
        [InlineKeyboardButton("Add Group", callback_data="add_group_prompt")],
        [InlineKeyboardButton("Remove Group", callback_data="remove_group_prompt")],
        [InlineKeyboardButton("Unauthorized Attempts", callback_data="list_attempts")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await send_response(update, "Select an option:", reply_markup=reply_markup)

@admin_only
async def button_handler(update: Update, context: CallbackContext):
    """Handles the menu buttons."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "list_groups":
        await list_groups(update, context)
    elif data == "add_group_prompt":
        await query.edit_message_text(
            "Send the group ID to add using the format:\n`/add_group <GROUP_ID>`",
            parse_mode="Markdown"
        )
    elif data == "remove_group_prompt":
        await remove_group(update, context)
    elif data.startswith("remove_"):
        # Extract chat_id from callback data (remove_CHAT_ID)
        chat_id_to_remove = data[7:]  # Remove "remove_" prefix
        await remove_group(update, context, chat_id_to_remove)
    elif data == "list_attempts":
        await list_unauthorized_attempts(update, context)

@admin_only
async def list_groups(update: Update, context: CallbackContext):
    """Lists authorized groups."""
    try:
        groups = get_all_groups()
        if not groups:
            response = "The bot is not in any authorized group."
        else:
            response = "Currently authorized groups:\n"
            response += "\n".join([f"- {group.get('name', 'N/A')} (ID: {group['_id']})" for group in groups])
        
        await send_response(update, response)
    except Exception as e:
        logger.error(f"Error listing groups: {e}")
        error_message = "An error occurred while listing the groups."
        await send_response(update, error_message)

@admin_only
async def add_group(update: Update, context: CallbackContext):
    """Adds a group to the authorized list."""
    if not context.args:
        await send_response(update, "Usage: /add_group <GROUP_ID>")
        return

    # Validate and normalize chat_id
    is_valid, result = validate_chat_id(context.args[0])
    if not is_valid:
        await send_response(update, result)
        return
    
    chat_id = result

    if is_group_allowed(chat_id):
        await send_response(update, f"The group with ID {chat_id} is already authorized.")
        return

    try:
        chat = await context.bot.get_chat(chat_id)
        chat_name = chat.title or "Unknown"
        db_add_group(chat_id, chat_name)
        logger.info(f"Group added by admin: {chat_name} (ID: {chat_id})")
        await send_response(update, f"Group added: {chat_name} (ID: {chat_id})")
    except TelegramError as e:
        logger.error(f"Error adding group {chat_id}: {e}")
        await send_response(update, f"Could not add group. Reason: {e.message}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while adding group {chat_id}: {e}")
        await send_response(update, "An unexpected error occurred.")

@admin_only
async def remove_group(update: Update, context: CallbackContext, chat_id_to_remove: str = None):
    """Removes an authorized group and makes the bot leave it."""
    if not chat_id_to_remove and context.args:
        chat_id_to_remove = context.args[0]
        if not chat_id_to_remove.startswith("-"):
            chat_id_to_remove = f"-{chat_id_to_remove}"

    if not chat_id_to_remove:
        groups = get_all_groups()
        if not groups:
            await send_response(update, "No authorized groups to display.")
            return
        keyboard = [
            [InlineKeyboardButton(group.get('name', 'N/A'), callback_data=f"remove_{group['_id']}")]
            for group in groups
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await send_response(update, "Select a group to remove:", reply_markup=reply_markup)
        return

    if not is_group_allowed(chat_id_to_remove):
        await send_response(update, f"The group with ID {chat_id_to_remove} is not authorized.")
        return

    try:
        db_remove_group(chat_id_to_remove)
        logger.info(f"Group removed: ID {chat_id_to_remove}")
        message = f"The group with ID {chat_id_to_remove} has been removed from the authorized list."
        
        await send_response(update, message)

        try:
            await context.bot.leave_chat(chat_id_to_remove)
            logger.info(f"The bot left the group with ID {chat_id_to_remove}.")
        except TelegramError as e:
            logger.error(f"Error leaving group {chat_id_to_remove}: {e}")
            error_message = f"Could not leave group. Reason: {e.message}"
            if update.callback_query:
                await update.callback_query.edit_message_text(f"{message}\n\n{error_message}")
            else:
                await update.message.reply_text(error_message)

    except Exception as e:
        logger.error(f"An unexpected error occurred while removing group {chat_id_to_remove}: {e}")
        await send_response(update, "An unexpected error occurred.")

@admin_only
async def list_unauthorized_attempts(update: Update, context: CallbackContext):
    """Lists unauthorized attempts to add the bot to groups."""
    try:
        attempts = get_unauthorized_attempts()
        if not attempts:
            response = "No unauthorized attempts have been recorded."
        else:
            response = "Unauthorized attempts (max 10 shown):\n\n"
            for attempt in attempts[:10]:
                response += (
                    f"- Group: {attempt.get('chat_name', 'N/A')} (ID: {attempt['chat_id']})\n"
                    f"  Added by: {attempt.get('added_by_name', 'N/A')} (ID: {attempt['added_by_id']})\n"
                    f"  Date: {attempt.get('timestamp', 'N/A')}\n\n"
                )
        
        await send_response(update, response)
    except Exception as e:
        logger.error(f"Error listing unauthorized attempts: {e}")
        await send_response(update, "An error occurred while listing unauthorized attempts.")

@admin_only
async def admin_help(update: Update, context: CallbackContext):
    """Displays available commands."""
    response = (
        "Available commands:\n"
        "/menu - Displays an interactive menu to manage groups.\n"
        "/list_groups - Lists all authorized groups.\n"
        "/add_group <GROUP_ID> - Adds an authorized group.\n"
        "/remove_group <GROUP_ID> - Removes an authorized group.\n"
        "/help - Displays this help message.\n"
    )
    await send_response(update, response)
