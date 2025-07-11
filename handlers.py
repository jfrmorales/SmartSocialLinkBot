import logging
import re
import json
from urllib.parse import urlparse, urlunparse
from telegram import Update, Chat, MessageEntity
from telegram.ext import CallbackContext
from db import is_group_allowed, add_group, log_unauthorized_group, remove_group

logger = logging.getLogger(__name__)

# Load domain mappings from the configuration file
with open("config/mappings.json", "r") as f:
    DOMAIN_MAPPINGS = json.load(f)

def escape_markdown_v2(text: str) -> str:
    """
    Escape special characters for MarkdownV2 in Telegram.
    """
    # Characters that need to be escaped in MarkdownV2
    escape_chars = '_*[]()~`>#+-=|{}.!'
    
    result = ""
    for char in text:
        if char in escape_chars:
            result += "\\" + char
        else:
            result += char
    
    return result

def format_message_with_links(text: str, url_mappings: dict) -> tuple:
    """
    Format message with proper MarkdownV2 escaping, separating text from links.
    Returns a tuple of (quoted_text, links_text)
    """
    # Remove URLs from the text to get just the message
    clean_text = text
    for old_url in url_mappings:
        clean_text = clean_text.replace(old_url, '').strip()
    
    # Escape and quote the clean text
    escaped_text = escape_markdown_v2(clean_text)
    quoted_text = f'"{escaped_text}"' if clean_text else ''
    
    # Create the links part
    links = []
    for old_url, new_url in url_mappings.items():
        links.append(f"[Modified link]({new_url})")
    
    links_text = '\n'.join(links)
    
    return quoted_text, links_text

def normalize_url(url: str) -> str:
    """
    Normalizes a URL by replacing its domain with a preferred one from the DOMAIN_MAPPINGS.
    It handles subdomains and preserves the rest of the URL structure.
    """
    try:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname

        if not hostname:
            return url

        for original_domain, replacement_domain in DOMAIN_MAPPINGS.items():
            if hostname.endswith(original_domain) and not hostname.endswith(replacement_domain):
                # Replace the domain and keep subdomains
                # Check if hostname is exactly the original domain or has a subdomain
                if hostname == original_domain:
                    new_hostname = replacement_domain
                elif hostname.endswith('.' + original_domain):
                    # Extract subdomain and append to replacement domain
                    subdomain = hostname[:-len(original_domain)-1]
                    new_hostname = subdomain + '.' + replacement_domain
                else:
                    # This means the domain is part of a larger domain name (e.g., "x.com" in "dominiox.com")
                    # So we skip this mapping
                    continue
                # Reconstruct the netloc to include credentials or port if they exist
                netloc_parts = [new_hostname]
                if parsed_url.port:
                    netloc_parts.append(str(parsed_url.port))
                new_netloc = ":".join(netloc_parts)
                if parsed_url.username:
                    userinfo = parsed_url.username
                    if parsed_url.password:
                        userinfo += ":" + parsed_url.password
                    new_netloc = f"{userinfo}@{new_netloc}"
                
                return urlunparse(parsed_url._replace(netloc=new_netloc))

        return url  # Return original URL if no mapping is found

    except Exception as e:
        logger.error(f"Error normalizing URL {url}: {e}")
        return url

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
    elif new_status in ["kicked", "left"]:
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
    user_name_escaped = escape_markdown_v2(update.message.from_user.first_name)
    user_mention = f"[{user_name_escaped}](tg://user?id={update.message.from_user.id})"

    url_pattern = re.compile(r"(https?://[^\s]+)")
    found_urls = url_pattern.findall(message_text)
    
    # Create a mapping of original URLs to their normalized versions
    url_mappings = {}
    has_changes = False
    for url in found_urls:
        new_url = normalize_url(url)
        if new_url != url:
            has_changes = True
        url_mappings[url] = new_url

    if has_changes:
        try:
            chat_member = await context.bot.get_chat_member(chat_id, context.bot.id)
            if chat_member.can_delete_messages:
                # Store the original message's topic ID before deleting
                original_thread_id = update.message.message_thread_id
                
                await context.bot.delete_message(chat_id, update.message.message_id)
                logger.info(f"Message deleted in group {chat_name} (ID: {chat_id}).")
                # Format the message with escaped text and clickable links
                quoted_text, links_text = format_message_with_links(message_text, url_mappings)
                message_parts = [f"Sent by {user_mention}"]
                if quoted_text:
                    message_parts.append(quoted_text)
                if links_text:
                    message_parts.append(links_text)
                new_message = '\n\n'.join(message_parts)
                
                # Send the new message with the same topic as the original
                await context.bot.send_message(
                    chat_id=chat_id, 
                    text=new_message,
                    message_thread_id=original_thread_id,
                    parse_mode="MarkdownV2"
                )
            else:
                logger.warning(f"Bot lacks permissions to delete messages in {chat_name} (ID: {chat_id}).")
                quoted_text, links_text = format_message_with_links(message_text, url_mappings)
                message_parts = []
                if quoted_text:
                    message_parts.append(quoted_text)
                if links_text:
                    message_parts.append(links_text)
                reply_message = '\n\n'.join(message_parts)
                await update.message.reply_text(reply_message, parse_mode="MarkdownV2")
        except Exception as e:
            logger.error(f"Error processing message in {chat_name} (ID: {chat_id}): {e}")
            # Try without markdown as fallback
            corrected_text = message_text
            for url, new_url in url_mappings.items():
                corrected_text = corrected_text.replace(url, new_url)
            await update.message.reply_text(corrected_text)