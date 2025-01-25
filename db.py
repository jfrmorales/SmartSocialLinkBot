from pymongo import MongoClient
import os
import logging

logger = logging.getLogger(__name__)

# Conexión a MongoDB
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]

def create_database():
    """Asegura que la colección exista."""
    if "groups" not in db.list_collection_names():
        db.create_collection("groups")
        logger.info("Base de datos inicializada.")

def add_group(chat_id, chat_name):
    """Agrega un grupo a la base de datos."""
    db.groups.update_one(
        {"_id": str(chat_id)},
        {"$set": {"name": chat_name}},
        upsert=True
    )

def remove_group(chat_id):
    """Elimina un grupo de la base de datos."""
    result = db.groups.delete_one({"_id": str(chat_id)})
    if result.deleted_count > 0:
        logger.info(f"Grupo eliminado de la base de datos: {chat_id}")
    else:
        logger.warning(f"No se encontró el grupo con ID {chat_id} en la base de datos.")

def get_all_groups():
    """Obtiene todos los grupos de la base de datos."""
    return list(db.groups.find({}, {"_id": 1, "name": 1}))

def is_group_allowed(chat_id):
    """Verifica si un grupo está en la base de datos."""
    return db.groups.count_documents({"_id": str(chat_id)}) > 0
