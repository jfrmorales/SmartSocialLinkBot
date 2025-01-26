from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from db import get_all_groups, add_group, remove_group, is_group_allowed, get_unauthorized_attempts
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def admin_only(func):
    """Decorador para comandos y callbacks que solo puede usar el administrador."""
    @wraps(func)
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = None
        if update.message:
            user_id = update.message.from_user.id
        elif update.callback_query:
            user_id = update.callback_query.from_user.id

        if user_id != context.bot_data["admin_id"]:
            if update.callback_query:
                await update.callback_query.answer("No tienes permisos para usar esta opción.", show_alert=True)
            else:
                await update.message.reply_text("No tienes permisos para usar este comando.")
            logger.warning(f"Usuario no autorizado intentó usar {func.__name__}: {user_id}")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

@admin_only
async def menu(update: Update, context: CallbackContext):
    """Muestra el menú interactivo para el administrador."""
    keyboard = [
        [InlineKeyboardButton("Listar Grupos", callback_data="listar_grupos")],
        [InlineKeyboardButton("Agregar Grupo", callback_data="agregar_grupo")],
        [InlineKeyboardButton("Eliminar Grupo", callback_data="eliminar_grupo")],
        [InlineKeyboardButton("Intentos no autorizados", callback_data="listar_intentos")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Selecciona una opción:", reply_markup=reply_markup)

@admin_only
async def button_handler(update: Update, context: CallbackContext):
    """Maneja los botones del menú."""
    query = update.callback_query
    await query.answer()

    if query.data == "listar_grupos":
        await listar_grupos(update, context)
    elif query.data == "agregar_grupo":
        await query.edit_message_text(
            "Envíame el ID del grupo a agregar usando el formato:\n`/agregar_grupo <ID_GRUPO>`", 
            parse_mode="Markdown"
        )
    elif query.data == "eliminar_grupo":
        await query.edit_message_text(
            "Envíame el ID del grupo a eliminar usando el formato:\n`/eliminar_grupo <ID_GRUPO>`", 
            parse_mode="Markdown"
        )
    elif query.data == "listar_intentos":
        await listar_intentos_no_autorizados(update, context)

@admin_only
async def listar_grupos(update: Update, context: CallbackContext):
    """Lista los grupos autorizados."""
    groups = get_all_groups()
    response = "Grupos actuales autorizados:\n" if groups else "El bot no está en ningún grupo."
    response += "\n".join([f"- {group['name']} (ID: {group['_id']})" for group in groups])
    if update.message:
        await update.message.reply_text(response)
    elif update.callback_query:
        await update.callback_query.edit_message_text(response)

@admin_only
async def agregar_grupo(update: Update, context: CallbackContext):
    """Agrega un grupo a la lista autorizada."""
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("Uso: /agregar_grupo <ID_GRUPO>")
        return

    chat_id = str(args[0])
    chat_name = "Desconocido"
    try:
        chat = await context.bot.get_chat(chat_id)
        chat_name = chat.title or "Desconocido"
    except Exception:
        logger.warning(f"No se pudo obtener el nombre del grupo con ID: {chat_id}")

    if is_group_allowed(chat_id):
        await update.message.reply_text(f"El grupo {chat_name} (ID: {chat_id}) ya está autorizado.")
        return

    add_group(chat_id, chat_name)
    logger.info(f"Grupo agregado por el administrador: {chat_name} (ID: {chat_id})")
    await update.message.reply_text(f"Grupo agregado: {chat_name} (ID: {chat_id})")

@admin_only
async def eliminar_grupo(update: Update, context: CallbackContext):
    """Elimina un grupo autorizado y hace que el bot salga del mismo."""
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("Uso: /eliminar_grupo <ID_GRUPO>")
        return

    chat_id = str(args[0])
    if not is_group_allowed(chat_id):
        await update.message.reply_text(f"El grupo con ID {chat_id} no está autorizado.")
        return

    remove_group(chat_id)
    logger.info(f"Grupo eliminado: ID {chat_id}")
    await update.message.reply_text(f"El grupo con ID {chat_id} ha sido eliminado de la lista autorizada.")

    try:
        await context.bot.leave_chat(chat_id)
        logger.info(f"El bot salió del grupo con ID {chat_id}.")
    except Exception as e:
        logger.error(f"Error al intentar salir del grupo con ID {chat_id}: {e}")
        await update.message.reply_text(f"Hubo un error al intentar salir del grupo con ID {chat_id}.")
        
@admin_only
async def listar_intentos_no_autorizados(update: Update, context: CallbackContext):
    """Lista los intentos no autorizados de añadir el bot a grupos."""
    attempts = get_unauthorized_attempts()
    if not attempts:
        await update.callback_query.edit_message_text("No se han registrado intentos no autorizados.")
        return

    response = "Intentos no autorizados:\n"
    for attempt in attempts:
        response += (
            f"- Grupo: {attempt['chat_name']} (ID: {attempt['chat_id']})\n"
            f"  Añadido por: {attempt['added_by_name']} (ID: {attempt['added_by_id']})\n"
            f"  Fecha: {attempt['timestamp']}\n\n"
        )
    await update.callback_query.edit_message_text(response)

@admin_only
async def admin_help(update: Update, context: CallbackContext):
    """Muestra los comandos disponibles."""
    response = (
        "Comandos disponibles:\n"
        "/menu - Muestra un menú interactivo para administrar grupos.\n"
        "/listar_grupos - Lista todos los grupos autorizados.\n"
        "/agregar_grupo <ID_GRUPO> - Agrega un grupo autorizado.\n"
        "/eliminar_grupo <ID_GRUPO> - Elimina un grupo autorizado.\n"
        "/help - Muestra este mensaje de ayuda.\n"
    )
    await update.message.reply_text(response)
