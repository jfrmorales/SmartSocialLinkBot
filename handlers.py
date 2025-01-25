from telegram import Update, Chat
from telegram.ext import CallbackContext
from db import is_group_allowed, add_group
import logging, re
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)

async def handle_group_join(update: Update, context: CallbackContext):
    """Gestiona cuando el bot es añadido a un grupo."""
    chat = update.effective_chat
    chat_id = str(chat.id)
    chat_name = chat.title or "Desconocido"

    # Verificar si el bot fue añadido al grupo
    new_status = update.my_chat_member.new_chat_member.status
    if new_status == "member":  # Bot añadido al grupo
        if is_group_allowed(chat_id):
            logger.info(f"El bot ya está autorizado en el grupo: {chat_name} (ID: {chat_id}).")
        else:
            # Verificar si el administrador fue quien añadió al bot
            if update.my_chat_member.from_user.id == context.bot_data["admin_id"]:
                logger.info(f"El administrador añadió el bot al grupo: {chat_name} (ID: {chat_id}). Registrando automáticamente...")
                add_group(chat_id, chat_name)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"El grupo '{chat_name}' (ID: {chat_id}) ha sido registrado automáticamente."
                )
            else:
                logger.warning(f"El bot fue añadido a un grupo no autorizado: {chat_name} (ID: {chat_id}). Saliendo...")
                try:
                    await context.bot.leave_chat(chat_id)
                    logger.info(f"El bot salió del grupo {chat_name} (ID: {chat_id}).")
                except Exception as e:
                    logger.error(f"Error al intentar salir del grupo {chat_name} (ID: {chat_id}): {e}")


async def process_message(update: Update, context: CallbackContext):
    """Procesa mensajes en grupos autorizados y corrige enlaces con dominios repetidos."""
    chat = update.effective_chat
    if chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        chat_id = str(chat.id)
        chat_name = chat.title or "Nombre desconocido"

        if not is_group_allowed(chat_id):
            logger.warning(f"Mensaje recibido de un grupo no autorizado: {chat_name} (ID: {chat_id})")
            return

        logger.info(f"Procesando mensaje en grupo autorizado: {chat_name} (ID: {chat_id})")

        # Verificar si el mensaje es válido
        if not update.message or not update.message.text:
            logger.warning(f"Actualización ignorada: No es un mensaje válido en {chat_name} (ID: {chat_id})")
            return

        message_text = update.message.text.strip()
        user_mention = f"[{update.message.from_user.first_name}](tg://user?id={update.message.from_user.id})"

        # Expresión regular para detectar dominios repetidos
        domain_regex = re.compile(
            r"(https?://(?:www\.)?(instagram\.com|twitter\.com|x\.com|tiktok\.com|fixupx\.com|ddinstagram\.com|vxtiktok\.com))((?:\2)+)"
        )

        def normalize_domain(match):
            base_domain = match.group(1)
            return base_domain

        corrected_text = domain_regex.sub(normalize_domain, message_text)

        # Ajuste para URLs deformadas específicamente con "fixup" repetido (p. ej. fixupfixupx.com)
        fixup_repeated_regex = re.compile(r"(https?://(?:www\.)?)(?:fixup)+(x\.com)")
        corrected_text = fixup_repeated_regex.sub(lambda m: f"{m.group(1)}fixupx.com", corrected_text)

        # Ajustes específicos para repeticiones de ciertos dominios base (opcional, si hay casos similares)
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

        # --- Paso final: parsear cada URL y forzar la normalización ---
        # Así nos aseguramos de que casos como "fixupfixupx" se queden en "fixupx.com",
        # "instagram.com" pase a "ddinstagram.com", etc. sin más repeticiones.
        url_pattern = re.compile(r"(https?://[^\s]+)")

        def final_normalize_url(original_url):
            try:
                parsed = urlparse(original_url)
                netloc = parsed.netloc.lower()

                # Normalizamos estos dominios principales
                # Si netloc contiene "instagram.com" => ddinstagram.com
                if "instagram.com" in netloc:
                    netloc = "ddinstagram.com"
                # Si netloc contiene "twitter.com" o "x.com" o "fixup" => fixupx.com
                elif "twitter.com" in netloc or "x.com" in netloc or "fixup" in netloc:
                    netloc = "fixupx.com"
                # Si netloc contiene "tiktok.com" => vxtiktok.com
                elif "tiktok.com" in netloc:
                    netloc = "vxtiktok.com"

                normalized = parsed._replace(netloc=netloc)
                return urlunparse(normalized)
            except Exception:
                # Si algo falla, regresamos la URL original sin cambios
                return original_url

        found_urls = url_pattern.findall(corrected_text)
        for url in found_urls:
            new_url = final_normalize_url(url)
            corrected_text = corrected_text.replace(url, new_url)
        # --- Fin del paso final de normalización ---

        # En este punto, corrected_text es el texto definitivo corregido
        # Mantenemos la variable 'modified_link' para reutilizar la lógica ya existente
        modified_link = corrected_text

        if modified_link != message_text:  # Solo actuamos si hubo algún cambio en las URLs
            try:
                chat_member = await context.bot.get_chat_member(chat_id, context.bot.id)
                if chat_member.can_delete_messages:
                    # Eliminar el mensaje original del usuario
                    await context.bot.delete_message(chat_id, update.message.message_id)
                    logger.info(f"Mensaje eliminado en el grupo {chat_name} (ID: {chat_id}).")

                    new_message = (
                        f"Enviado por {user_mention}\n\n"
                        f"[Enlace modificado]({modified_link})"
                    )
                    await context.bot.send_message(chat_id=chat_id, text=new_message, parse_mode="Markdown")
                else:
                    logger.warning(f"El bot no tiene permisos para borrar mensajes en {chat_name} (ID: {chat_id}).")
                    reply_message = (
                        f"Enviado por {user_mention}\n\n"
                        f"[Enlace modificado]({modified_link})"
                    )
                    await update.message.reply_text(reply_message, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Error al intentar procesar el mensaje en {chat_name} (ID: {chat_id}): {e}")
                fallback_message = (
                    f"Enviado por {user_mention}\n\n"
                    f"[Enlace modificado]({modified_link})"
                )
                await update.message.reply_text(fallback_message, parse_mode="Markdown")
