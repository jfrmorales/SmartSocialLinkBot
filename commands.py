from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from db import get_all_groups, add_group, remove_group as db_remove_group, is_group_allowed, get_unauthorized_attempts
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def admin_only(func):
    """Decorator for commands and callbacks that only the admin can use."""
    @wraps(func)
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = None
        if update.message:
            user_id = update.message.from_user.id
        elif update.callback_query:
            user_id = update.callback_query.from_user.id

        if user_id != context.bot_data["admin_id"]:
            if update.callback_query:
                await update.callback_query.answer("You do not have permission to use this option.", show_alert=True)
            else:
                await update.message.reply_text("You do not have permission to use this command.")
            logger.warning(f"Unauthorized user attempted to use {func.__name__}: {user_id}")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

@admin_only
async def menu(update: Update, context: CallbackContext):
    """Displays the interactive menu for the admin."""
    keyboard = [
        [InlineKeyboardButton("List Groups", callback_data="list_groups")],
        [InlineKeyboardButton("Add Group", callback_data="add_group")],
        [InlineKeyboardButton("Remove Group", callback_data="remove_group")],
        [InlineKeyboardButton("Unauthorized Attempts", callback_data="list_attempts")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select an option:", reply_markup=reply_markup)

@admin_only
async def button_handler(update: Update, context: CallbackContext):
    """Handles the menu buttons."""
    query = update.callback_query
    await query.answer()

    if query.data == "list_groups":
        await list_groups(update, context)
    elif query.data == "add_group":
        await query.edit_message_text(
            "Send me the group ID to add using the format:\n`/add_group <GROUP_ID>`", 
            parse_mode="Markdown"
        )
    elif query.data == "remove_group":
        groups = get_all_groups()
        if not groups:
            await query.edit_message_text("No authorized groups to display.")
            return

        keyboard = [
            [InlineKeyboardButton(group["name"], callback_data=f"remove_{group['_id']}")]
            for group in groups
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Select a group to remove:", reply_markup=reply_markup)

    elif query.data.startswith("remove_"):
        chat_id = query.data.split("_")[1]
        chat_name = next(
            (group["name"] for group in get_all_groups() if group["_id"] == chat_id),
            "Unknown"
        )

        # Fix the call to remove_group
        db_remove_group(chat_id)
        logger.info(f"Group removed via button: {chat_name} (ID: {chat_id})")
        await query.edit_message_text(f"The group '{chat_name}' (ID: {chat_id}) has been removed from the authorized list.")

        try:
            await context.bot.leave_chat(chat_id)
            logger.info(f"The bot left the group with ID {chat_id}.")
        except Exception as e:
            logger.error(f"Error trying to leave the group with ID {chat_id}: {e}")
            await query.message.reply_text(f"An error occurred while trying to leave the group with ID {chat_id}.")

@admin_only
async def list_groups(update: Update, context: CallbackContext):
    """Lists authorized groups."""
    groups = get_all_groups()
    response = "Currently authorized groups:\n" if groups else "The bot is not in any group."
    response += "\n".join([f"- {group['name']} (ID: {group['_id']})" for group in groups])
    if update.message:
        await update.message.reply_text(response)
    elif update.callback_query:
        await update.callback_query.edit_message_text(response)

@admin_only
async def add_group(update: Update, context: CallbackContext):
    """Adds a group to the authorized list."""
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("Usage: /add_group <GROUP_ID>")
        return

    # Ensure the group ID is negative
    chat_id = str(args[0])
    if not chat_id.startswith("-"):
        chat_id = f"-{chat_id}"

    chat_name = "Unknown"
    try:
        chat = await context.bot.get_chat(chat_id)
        chat_name = chat.title or "Unknown"
    except Exception:
        logger.warning(f"Could not retrieve the group name for ID: {chat_id}")

    if is_group_allowed(chat_id):
        await update.message.reply_text(f"The group {chat_name} (ID: {chat_id}) is already authorized.")
        return

    add_group(chat_id, chat_name)
    logger.info(f"Group added by admin: {chat_name} (ID: {chat_id})")
    await update.message.reply_text(f"Group added: {chat_name} (ID: {chat_id})")

@admin_only
async def remove_group(update: Update, context: CallbackContext):
    """Removes an authorized group and makes the bot leave it."""
    args = context.args

    # If no ID is provided, display a list of groups with buttons
    if len(args) < 1:
        groups = get_all_groups()
        if not groups:
            await update.message.reply_text("No authorized groups to display.")
            return

        keyboard = [
            [InlineKeyboardButton(group["name"], callback_data=f"remove_{group['_id']}")]
            for group in groups
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Select a group to remove:", reply_markup=reply_markup)
        return

    # Proceed with removal if ID is provided
    chat_id = str(args[0])
    if not chat_id.startswith("-"):
        chat_id = f"-{chat_id}"

    if not is_group_allowed(chat_id):
        await update.message.reply_text(f"The group with ID {chat_id} is not authorized.")
        return

    remove_group(chat_id)
    logger.info(f"Group removed: ID {chat_id}")
    await update.message.reply_text(f"The group with ID {chat_id} has been removed from the authorized list.")

    try:
        await context.bot.leave_chat(chat_id)
        logger.info(f"The bot left the group with ID {chat_id}.")
    except Exception as e:
        logger.error(f"Error trying to leave the group with ID {chat_id}: {e}")
        await update.message.reply_text(f"An error occurred while trying to leave the group with ID {chat_id}.")

@admin_only
async def list_unauthorized_attempts(update: Update, context: CallbackContext):
    """Lists unauthorized attempts to add the bot to groups."""
    attempts = get_unauthorized_attempts()
    if not attempts:
        await update.callback_query.edit_message_text("No unauthorized attempts have been recorded.")
        return

    response = "Unauthorized attempts:\n"
    for attempt in attempts:
        response += (
            f"- Group: {attempt['chat_name']} (ID: {attempt['chat_id']})\n"
            f"  Added by: {attempt['added_by_name']} (ID: {attempt['added_by_id']})\n"
            f"  Date: {attempt['timestamp']}\n\n"
        )
    await update.callback_query.edit_message_text(response)

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
    await update.message.reply_text(response)
