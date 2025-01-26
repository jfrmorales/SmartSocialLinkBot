from telegram import Update, Chat
from telegram.ext import CallbackContext
from db import is_group_allowed, add_group, log_unauthorized_group, remove_group
import logging, re
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)

async def handle_group_join(update: Update, context: CallbackContext):
    """Handles when the bot is added or removed from a group."""
    chat = update.effective_chat
    chat_id = str(chat.id)
    chat_name = chat.title or "Unknown"
    added_or_removed_by = update.my_chat_member.from_user

    new_status = update.my_chat_member.new_chat_member.status
    old_status = update.my_chat_member.old_chat_member.status

    if new_status == "member":  # Bot added to the group
        if is_group_allowed(chat_id):
            logger.info(f"The bot is already authorized in the group: {chat_name} (ID: {chat_id}).")
        else:
            if added_or_removed_by.id == context.bot_data["admin_id"]:
                logger.info(f"The admin added the bot to the group: {chat_name} (ID: {chat_id}). Automatically registering...")
                add_group(chat_id, chat_name)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"The group '{chat_name}' (ID: {chat_id}) has been registered automatically."
                )
            else:
                log_unauthorized_group(
                    chat_id=chat_id,
                    chat_name=chat_name,
                    added_by_id=added_or_removed_by.id,
                    added_by_name=f"{added_or_removed_by.first_name} {added_or_removed_by.last_name or ''}".strip()
                )
                logger.warning(f"The bot was added to an unauthorized group: {chat_name} (ID: {chat_id}). Leaving...")
                await context.bot.leave_chat(chat_id)
    elif new_status in ["kicked", "left"]:  # Bot removed from the group
        if is_group_allowed(chat_id):
            logger.info(f"The bot was removed from an authorized group: {chat_name} (ID: {chat_id}). Removing from the database...")
            remove_group(chat_id)
            logger.info(f"The group '{chat_name}' (ID: {chat_id}) has been removed from the authorized list.")

async def process_message(update: Update, context: CallbackContext):
    """Processes messages in authorized groups and fixes repeated domain links."""
    chat = update.effective_chat
    if chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        chat_id = str(chat.id)
        chat_name = chat.title or "Unknown"

        if not is_group_allowed(chat_id):
            logger.warning(f"Message received from an unauthorized group: {chat_name} (ID: {chat_id})")
            return

        logger.info(f"Processing message in authorized group: {chat_name} (ID: {chat_id})")

        # Check if the message is valid
        if not update.message or not update.message.text:
            logger.warning(f"Update ignored: Not a valid message in {chat_name} (ID: {chat_id})")
            return

        message_text = update.message.text.strip()
        user_mention = f"[{update.message.from_user.first_name}](tg://user?id={update.message.from_user.id})"

        # Regex to detect repeated domains
        domain_regex = re.compile(
            r"(https?://(?:www\.)?(instagram\.com|twitter\.com|x\.com|tiktok\.com|fixupx\.com|ddinstagram\.com|vxtiktok\.com))((?:\2)+)"
        )

        def normalize_domain(match):
            base_domain = match.group(1)
            return base_domain

        corrected_text = domain_regex.sub(normalize_domain, message_text)

        # Specific adjustment for malformed URLs with repeated "fixup"
        fixup_repeated_regex = re.compile(r"(https?://(?:www\.)?)(?:fixup)+(x\.com)")
        corrected_text = fixup_repeated_regex.sub(lambda m: f"{m.group(1)}fixupx.com", corrected_text)

        # Adjustments for specific repeated base domains
        instagram_repeated_regex = re.compile(r"(https?://(?:www\.)?)(?:instagram)+(\.com)")
        corrected_text = instagram_repeated_regex.sub(lambda m: f"{m.group(1)}instagram.com", corrected_text)

        ddinstagram_repeated_regex = re.compile(r"(https?://(?:www\.)?)(?:ddinstagram)+(\.com)")
        corrected_text = ddinstagram_repeated_regex.sub(lambda m: f"{m.group(1)}ddinstagram.com", corrected_text)

        tiktok_repeated_regex = re.compile(r"(https?://(?:www\.)?)(?:tiktok)+(\.com)")
        corrected_text = tiktok_repeated_regex.sub(lambda m: f"{m.group(1)}tiktok.com", corrected_text)

        vxtiktok_repeated_regex = re.compile(r"(https?://(?:www\.)?)(?:vxtiktok)+(\.com)")
        corrected_text = vxtiktok_repeated_regex.sub(lambda m: f"{m.group(1)}vxtiktok.com", corrected_text)

        twitter_repeated_regex = re.compile(r"(https?://(?:www\.)?)(?:twitter)+(\.com)")
        corrected_text = twitter_repeated_regex.sub(lambda m: f"{m.group(1)}twitter.com", corrected_text)

        x_repeated_regex = re.compile(r"(https?://(?:www\.)?)(?:x)+(\.com)")
        corrected_text = x_repeated_regex.sub(lambda m: f"{m.group(1)}x.com", corrected_text)

        # Final step: Parse each URL and enforce normalization
        url_pattern = re.compile(r"(https?://[^\s]+)")

        def final_normalize_url(original_url):
            try:
                parsed = urlparse(original_url)
                netloc = parsed.netloc.lower()

                # Normalize main domains
                if "instagram.com" in netloc:
                    netloc = "ddinstagram.com"
                elif "twitter.com" in netloc or "x.com" in netloc or "fixup" in netloc:
                    netloc = "fixupx.com"
                elif "tiktok.com" in netloc:
                    netloc = "vxtiktok.com"

                normalized = parsed._replace(netloc=netloc)
                return urlunparse(normalized)
            except Exception:
                return original_url

        found_urls = url_pattern.findall(corrected_text)
        for url in found_urls:
            new_url = final_normalize_url(url)
            corrected_text = corrected_text.replace(url, new_url)

        modified_link = corrected_text

        if modified_link != message_text:  # Act only if changes were made
            try:
                chat_member = await context.bot.get_chat_member(chat_id, context.bot.id)
                if chat_member.can_delete_messages:
                    await context.bot.delete_message(chat_id, update.message.message_id)
                    logger.info(f"Message deleted in group {chat_name} (ID: {chat_id}).")

                    new_message = (
                        f"Sent by {user_mention}\n\n"
                        f"[Modified link]({modified_link})"
                    )
                    await context.bot.send_message(chat_id=chat_id, text=new_message, parse_mode="Markdown")
                else:
                    logger.warning(f"The bot does not have permissions to delete messages in {chat_name} (ID: {chat_id}).")
                    reply_message = (
                        f"Sent by {user_mention}\n\n"
                        f"[Modified link]({modified_link})"
                    )
                    await update.message.reply_text(reply_message, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Error processing message in {chat_name} (ID: {chat_id}): {e}")
                fallback_message = (
                    f"Sent by {user_mention}\n\n"
                    f"[Modified link]({modified_link})"
                )
                await update.message.reply_text(fallback_message, parse_mode="Markdown")
