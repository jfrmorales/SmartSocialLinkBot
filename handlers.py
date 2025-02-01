import logging
import re
from urllib.parse import urlparse, urlunparse
from telegram import Update, Chat
from telegram.ext import CallbackContext
from db import is_group_allowed, add_group, log_unauthorized_group, remove_group

logger = logging.getLogger(__name__)

def normalize_netloc(netloc: str) -> str:
    """
    Normalize the netloc by ensuring that the second-level domain (SLD)
    matches one of the allowed services. For example, if the SLD is
    "tiktok" (or a repetition like "tiktiktiktok"), it will be replaced by "vxtiktok".
    Subdomains (e.g. "vm.tiktok.com") are preserved.
    """
    parts = netloc.split('.')
    if len(parts) < 2:
        return netloc.lower()
    subdomains = parts[:-2]
    sld = parts[-2]
    tld = parts[-1]
    sld_lower = sld.lower()

    # Mapping: if the SLD is (possibly repeated) one of these keys, then replace it
    mappings = {
        "instagram": "ddinstagram",
        "twitter": "fixupx",
        "x": "fixupx",
        "fixupx": "fixupx",
        "tiktok": "vxtiktok"
    }
    for key, replacement in mappings.items():
        # Match one or more repetitions of the key (case-insensitive)
        pattern = re.compile(rf'^(?:{key})+$', re.IGNORECASE)
        if pattern.match(sld_lower):
            sld_lower = replacement
            break
    new_netloc = '.'.join(subdomains + [sld_lower, tld])
    return new_netloc

def final_normalize_url(original_url: str) -> str:
    """
    Parses the original URL, normalizes its netloc and scheme, and returns the corrected URL.
    For TikTok URLs, only the 'tiktok' portion is replaced with 'vxtiktok' (e.g. vm.tiktok.com -> vm.vxtiktok.com).
    """
    try:
        parsed = urlparse(original_url)
        normalized_netloc = normalize_netloc(parsed.netloc)
        normalized_scheme = parsed.scheme.lower()
        normalized = parsed._replace(scheme=normalized_scheme, netloc=normalized_netloc)
        return urlunparse(normalized)
    except Exception as e:
        logger.error(f"Error normalizing URL {original_url}: {e}")
        return original_url

async def handle_group_join(update: Update, context: CallbackContext):
    """Handles the bot being added or removed from a group."""
    chat = update.effective_chat
    chat_id = str(chat.id)
    chat_name = chat.title or "Unknown"
    added_or_removed_by = update.my_chat_member.from_user

    new_status = update.my_chat_member.new_chat_member.status
    old_status = update.my_chat_member.old_chat_member.status

    if new_status == "member":  # Bot added
        if is_group_allowed(chat_id):
            logger.info(f"Bot is already authorized in group: {chat_name} (ID: {chat_id}).")
        else:
            if added_or_removed_by.id == context.bot_data["admin_id"]:
                logger.info(f"Admin added bot to group: {chat_name} (ID: {chat_id}). Automatically registering...")
                add_group(chat_id, chat_name)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"The group '{chat_name}' (ID: {chat_id}) has been automatically registered."
                )
            else:
                log_unauthorized_group(
                    chat_id=chat_id,
                    chat_name=chat_name,
                    added_by_id=added_or_removed_by.id,
                    added_by_name=f"{added_or_removed_by.first_name} {added_or_removed_by.last_name or ''}".strip()
                )
                logger.warning(f"Bot was added to an unauthorized group: {chat_name} (ID: {chat_id}). Leaving...")
                await context.bot.leave_chat(chat_id)
    elif new_status in ["kicked", "left"]:  # Bot removed
        if is_group_allowed(chat_id):
            logger.info(f"Bot was removed from an authorized group: {chat_name} (ID: {chat_id}). Removing from database...")
            remove_group(chat_id)
            logger.info(f"Group '{chat_name}' (ID: {chat_id}) has been removed from the authorized list.")

async def process_message(update: Update, context: CallbackContext):
    """
    Processes messages in authorized groups. It finds all URLs in the message,
    normalizes them (ensuring correct domain names), and if any corrections are made,
    either deletes the original message (if the bot has admin permissions) and sends a new one
    with a "Sent by" attribution, or replies to the message without the attribution.
    """
    chat = update.effective_chat
    if chat.type not in [Chat.GROUP, Chat.SUPERGROUP]:
        return

    chat_id = str(chat.id)
    chat_name = chat.title or "Unknown"

    if not is_group_allowed(chat_id):
        logger.warning(f"Message received from unauthorized group: {chat_name} (ID: {chat_id}).")
        return

    if not update.message or not update.message.text:
        logger.warning(f"Ignored update: not a valid message in {chat_name} (ID: {chat_id}).")
        return

    message_text = update.message.text.strip()
    user_mention = f"[{update.message.from_user.first_name}](tg://user?id={update.message.from_user.id})"

    url_pattern = re.compile(r"(https?://[^\s]+)")
    found_urls = url_pattern.findall(message_text)
    corrected_text = message_text
    for url in found_urls:
        new_url = final_normalize_url(url)
        corrected_text = corrected_text.replace(url, new_url)

    if corrected_text != message_text:
        try:
            chat_member = await context.bot.get_chat_member(chat_id, context.bot.id)
            if chat_member.can_delete_messages:
                await context.bot.delete_message(chat_id, update.message.message_id)
                logger.info(f"Message deleted in group {chat_name} (ID: {chat_id}).")
                new_message = (
                    f"Sent by {user_mention}\n\n"
                    f"[Modified link]({corrected_text})"
                )
                await context.bot.send_message(chat_id=chat_id, text=new_message, parse_mode="Markdown")
            else:
                logger.warning(f"Bot lacks permissions to delete messages in {chat_name} (ID: {chat_id}).")
                reply_message = f"[Modified link]({corrected_text})"
                await update.message.reply_text(reply_message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error processing message in {chat_name} (ID: {chat_id}): {e}")
            fallback_message = f"[Modified link]({corrected_text})"
            await update.message.reply_text(fallback_message, parse_mode="Markdown")
