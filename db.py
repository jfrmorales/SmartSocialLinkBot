from pymongo import MongoClient
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# MongoDB connection
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]

def create_database():
    """Ensures the collection exists."""
    if "groups" not in db.list_collection_names():
        db.create_collection("groups")
        logger.info("Database initialized.")

def add_group(chat_id, chat_name):
    """Adds a group to the database."""
    db.groups.update_one(
        {"_id": str(chat_id)},
        {"$set": {"name": chat_name}},
        upsert=True
    )

def remove_group(chat_id):
    """Removes a group from the database."""
    result = db.groups.delete_one({"_id": str(chat_id)})
    if result.deleted_count > 0:
        logger.info(f"Group removed from the database: {chat_id}")
    else:
        logger.warning(f"Group with ID {chat_id} not found in the database.")

def get_all_groups():
    """Retrieves all groups from the database."""
    return list(db.groups.find({}, {"_id": 1, "name": 1}))

def is_group_allowed(chat_id):
    """Checks if a group is in the database."""
    return db.groups.count_documents({"_id": str(chat_id)}) > 0

def log_unauthorized_group(chat_id, chat_name, added_by_id, added_by_name):
    """Logs an unauthorized attempt to add the bot to a group."""
    db.unauthorized_groups.insert_one({
        "chat_id": chat_id,
        "chat_name": chat_name,
        "added_by_id": added_by_id,
        "added_by_name": added_by_name,
        "timestamp": datetime.now()
    })

def get_unauthorized_attempts():
    """Retrieves all logged unauthorized attempts."""
    return list(db.unauthorized_groups.find({}, {"_id": 0}))
