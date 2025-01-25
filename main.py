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
from commands import menu, listar_grupos, agregar_grupo, eliminar_grupo, admin_help, button_handler
from handlers import process_message, handle_group_join

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv(dotenv_path="config/.env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

if not BOT_TOKEN or not ADMIN_ID:
    raise ValueError("El token del bot o el ID del administrador no están definidos en el archivo .env")

def main():
    # Verificar o crear la base de datos al iniciar
    create_database()

    # Crear la aplicación del bot
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Configurar datos globales del bot
    app.bot_data["admin_id"] = ADMIN_ID

    # Manejadores de comandos
    app.add_handler(CommandHandler("menu", menu))  # Menú interactivo
    app.add_handler(CommandHandler("listar_grupos", listar_grupos))
    app.add_handler(CommandHandler("agregar_grupo", agregar_grupo))
    app.add_handler(CommandHandler("eliminar_grupo", eliminar_grupo))
    app.add_handler(CommandHandler("help", admin_help))

    # Manejadores de botones del menú
    app.add_handler(CallbackQueryHandler(button_handler))

    # Manejadores de mensajes
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, process_message))

    # Manejador para eventos cuando el bot es añadido a un grupo
    app.add_handler(ChatMemberHandler(handle_group_join, ChatMemberHandler.MY_CHAT_MEMBER))

    # Iniciar el bot
    logger.info("Bot iniciado y en ejecución...")
    app.run_polling()

if __name__ == "__main__":
    main()
