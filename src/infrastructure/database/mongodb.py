from typing import Optional, Dict, Any, List

import motor.motor_asyncio
from bson import ObjectId

from src.config.config import settings
from src.utils.logger import logger
from .constants import Collections, FileFields

# Thread-local storage for MongoDB clients
import threading
_thread_local = threading.local()


def get_mongo_client():
    """Get MongoDB client - creates new instance per thread for safety."""
    if not hasattr(_thread_local, 'client') or _thread_local.client is None:
        logger.info("Creating new MongoDB client for thread", thread_id=threading.get_ident())
        _thread_local.client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGO_URI)
        _thread_local.db = _thread_local.client[settings.MONGO_DB]
    return _thread_local.client, _thread_local.db


async def get_collection(collection_name: str):
    """Get a MongoDB collection."""
    _, db = get_mongo_client()
    return db[collection_name]


async def ping_mongodb():
    """Check if MongoDB connection is alive."""
    try:
        client, _ = get_mongo_client()
        await client.admin.command('ping')
        return True
    except Exception:
        return False


async def close_mongodb():
    """Close MongoDB connection for current thread."""
    if hasattr(_thread_local, 'client') and _thread_local.client:
        _thread_local.client.close()
        _thread_local.client = None


# File operations
async def get_file_by_id(file_id: str) -> Optional[Dict[str, Any]]:
    """
    Get file document by ID

    Args:
        file_id: File document ID

    Returns:
        File document or None if not found
    """
    try:
        collection = await get_collection(Collections.FILES)

        # Convert string ID to ObjectId if needed
        if isinstance(file_id, str):
            object_id = ObjectId(file_id)
        else:
            object_id = file_id

        file_doc = await collection.find_one({FileFields.ID: object_id})

        if file_doc:
            logger.info(
                "File found in MongoDB",
                file_id=file_id,
                file_name=file_doc.get(FileFields.FILE_NAME),
                file_type=file_doc.get(FileFields.FILE_TYPE),
                file_size=file_doc.get(FileFields.FILE_SIZE)
            )
        else:
            logger.warning("File not found in MongoDB", file_id=file_id)

        return file_doc

    except Exception as e:
        logger.error(
            "Error getting file from MongoDB",
            file_id=file_id,
            error_type=type(e).__name__,
            error_message=str(e)
        )
        raise


async def get_files_by_owner(owner_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get files by owner ID

    Args:
        owner_id: Owner user ID
        limit: Maximum number of files to return

    Returns:
        List of file documents
    """
    try:
        collection = await get_collection(Collections.FILES)

        cursor = collection.find({FileFields.OWNER_ID: owner_id}).limit(limit)
        files = await cursor.to_list(length=limit)

        logger.info(
            "Files retrieved by owner",
            owner_id=owner_id,
            files_count=len(files)
        )

        return files

    except Exception as e:
        logger.error(
            "Error getting files by owner",
            owner_id=owner_id,
            error_type=type(e).__name__,
            error_message=str(e)
        )
        raise





async def create_embedding_record(embedding_data: Dict[str, Any]) -> str:
    """
    Create embedding record in MongoDB

    Args:
        embedding_data: Embedding metadata

    Returns:
        Created record ID
    """
    try:
        collection = await get_collection(Collections.EMBEDDINGS)

        result = await collection.insert_one(embedding_data)

        logger.info(
            "Embedding record created",
            record_id=str(result.inserted_id),
            file_id=embedding_data.get("file_id"),
            user_id=embedding_data.get("user_id")
        )

        return str(result.inserted_id)

    except Exception as e:
        logger.error(
            "Error creating embedding record",
            error_type=type(e).__name__,
            error_message=str(e)
        )
        raise


async def get_embedding_records_by_file(file_id: str) -> List[Dict[str, Any]]:
    """
    Get embedding records by file ID

    Args:
        file_id: File document ID

    Returns:
        List of embedding records
    """
    try:
        collection = await get_collection(Collections.EMBEDDINGS)

        cursor = collection.find({"file_id": file_id})
        records = await cursor.to_list(length=None)

        logger.info(
            "Embedding records retrieved by file",
            file_id=file_id,
            records_count=len(records)
        )

        return records

    except Exception as e:
        logger.error(
            "Error getting embedding records by file",
            file_id=file_id,
            error_type=type(e).__name__,
            error_message=str(e)
        )
        raise


async def delete_embedding_records_by_file(file_id: str) -> int:
    """
    Delete embedding records by file ID

    Args:
        file_id: File document ID

    Returns:
        Number of deleted records
    """
    try:
        collection = await get_collection(Collections.EMBEDDINGS)

        result = await collection.delete_many({"file_id": file_id})
        deleted_count = result.deleted_count

        logger.info(
            "Embedding records deleted by file",
            file_id=file_id,
            deleted_count=deleted_count
        )

        return deleted_count

    except Exception as e:
        logger.error(
            "Error deleting embedding records by file",
            file_id=file_id,
            error_type=type(e).__name__,
            error_message=str(e)
        )
        raise
