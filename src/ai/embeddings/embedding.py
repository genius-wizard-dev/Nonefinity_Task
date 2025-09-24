import asyncio
import time
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import threading

from celery import shared_task

from src.ai.common import LangChainTextProcessor
from src.infrastructure.database import (
    QdrantService, get_file_by_id, create_embedding_record
)
from src.infrastructure.storage import MinioService
from src.utils.logger import logger
from .embedder_registry import EmbedderRegistry


def run_async_in_thread(async_func, *args, **kwargs):
    """
    Safely run async function in a new thread with its own event loop.
    This prevents conflicts with existing event loops in Celery workers.
    """
    def run_in_new_loop():
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            logger.info(f"Running async function {async_func.__name__} in new thread", thread_id=threading.get_ident())
            result = loop.run_until_complete(async_func(*args, **kwargs))
            logger.info(f"Async function {async_func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Async function {async_func.__name__} failed: {e}", error_type=type(e).__name__)
            raise
        finally:
            loop.close()

    # Run in a separate thread
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run_in_new_loop)
        return future.result()


@shared_task(name="tasks.embedding.run_embedding", bind=True)
def run_embedding(
    self,
    user_id: str,
    file_id: str = None,
    chunks: List[str] = None,
    provider: str = "openai",
    model_id: str = "text-embedding-ada-002",
    credential: Dict[str, Any] = None,
    split_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Unified task to create embeddings from text chunks or files and save to Qdrant.

    Args:
        user_id: User identifier
        file_id: File identifier (if processing file from Minio)
        chunks: List of text chunks to embed (if processing chunks directly)
        provider: Embedding provider (openai, huggingface)
        model_id: Model identifier
        credential: Dictionary containing API keys and other credentials
        split_config: Configuration for text splitting when processing files

    Returns:
        Dictionary with task status and results
    """
    start_time = time.time()

    try:

        # Process file if file_id provided and no chunks
        if file_id and not chunks:
            chunks = run_async_in_thread(_process_file_for_embedding, file_id, split_config)

        if not chunks:
            raise ValueError("No chunks provided for embedding")

        # Get embedder from registry (with caching)
        embedder = EmbedderRegistry.get_embedder(provider, model_id, credential)

        # Create embeddings for all chunks
        logger.info("Creating embeddings for chunks")
        vectors = embedder.embed_documents(chunks)

        if not vectors:
            raise ValueError("No embeddings were generated")

        logger.info(
            "Embeddings created successfully",
            vectors_count=len(vectors),
            vector_dimension=len(vectors[0]) if vectors else 0
        )

        # Save to Qdrant
        logger.info("Saving embeddings to Qdrant")
        qdrant = QdrantService()
        save_result = qdrant.save_embeddings(user_id, file_id or "chunks", chunks, vectors)

        # Create embedding record in MongoDB if file_id provided
        embedding_record_id = None
        if file_id:
            embedding_data = {
                "file_id": file_id,
                "user_id": user_id,
                "provider": provider,
                "model_id": model_id,
                "chunks_count": len(chunks),
                "vector_dimension": len(vectors[0]) if vectors else 0,
                "split_config": split_config,
                "created_at": time.time(),
                "qdrant_operation": save_result
            }
            embedding_record_id = run_async_in_thread(create_embedding_record, embedding_data)

        processing_time = time.time() - start_time

        result = {
            "status": "success",
            "file_id": file_id,
            "user_id": user_id,
            "chunks_processed": len(chunks),
            "vectors_created": len(vectors),
            "vector_dimension": len(vectors[0]) if vectors else 0,
            "provider": provider,
            "model_id": model_id,
            "processing_time_seconds": round(processing_time, 2),
            "qdrant_operation": save_result,
            "embedding_record_id": embedding_record_id,
            "split_config": split_config,
        }

        logger.info(
            "Embedding task completed successfully",
            task_id=self.request.id,
            **result
        )

        return result

    except Exception as e:
        processing_time = time.time() - start_time
        error_result = {
            "status": "error",
            "file_id": file_id,
            "user_id": user_id,
            "provider": provider,
            "model_id": model_id,
            "error_message": str(e),
            "error_type": type(e).__name__,
            "processing_time_seconds": round(processing_time, 2),
        }

        logger.error(
            "Embedding task failed",
            task_id=self.request.id,
            **error_result
        )

        # Re-raise exception so Celery can handle retries
        self.retry(countdown=60, max_retries=3, exc=e)


async def _process_file_for_embedding(file_id: str, split_config: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    Helper function to process file and extract chunks for embedding

    Args:
        file_id: File ID in MongoDB
        split_config: Configuration for text splitting

    Returns:
        List of text chunks
    """
    logger.info(
        "Starting file processing for embedding",
        file_id=file_id,
        split_config=split_config,
        thread_id=threading.get_ident()
    )

    # Set default split config
    if split_config is None:
        split_config = {"chunk_size": 1000, "chunk_overlap": 200}

    try:
        # Get file info from MongoDB
        logger.info("Fetching file from MongoDB", file_id=file_id)
        file_doc = await get_file_by_id(file_id)
        logger.info("File fetched successfully", file_id=file_id, has_doc=file_doc is not None)
    except Exception as e:
        logger.error("Error getting file from MongoDB", file_id=file_id, error_type=type(e).__name__, error_message=str(e))
        raise
    if not file_doc:
        raise ValueError(f"File not found: {file_id}")

    # Extract file metadata
    bucket = file_doc.get("bucket")
    file_path = file_doc.get("file_path")
    file_name = file_doc.get("file_name", "")
    file_type = file_doc.get("file_type", "")
    file_url = file_doc.get("url", "")

    # Update file status to processing
    # Initialize services
    minio_service = MinioService()
    text_processor = LangChainTextProcessor()

    # Check if file type is supported
    if not text_processor.is_supported_file_type(file_type):
        raise ValueError(f"Unsupported file type: {file_type}")

    # Download file from Minio
    if file_url:
        file_content = minio_service.download_file_by_url(file_url)
    else:
        file_content = minio_service.download_file_by_path(bucket, file_path)

    # Process file content with LangChain
    documents = text_processor.process_file_content(
        content=file_content,
        file_type=file_type,
        file_name=file_name,
        split_config=split_config
    )

    if not documents:
        raise ValueError("No documents extracted from file")

    # Extract text chunks from documents
    final_chunks = text_processor.extract_text_chunks(documents)

    if not final_chunks:
        raise ValueError("No text content extracted from documents")

    return final_chunks


@shared_task(name="tasks.embedding.search_similar")
def search_similar(
    query_text: str,
    provider: str,
    model_id: str,
    credential: Dict[str, Any],
    user_id: str = None,
    file_id: str = None,
    limit: int = 5
) -> Dict[str, Any]:
    """
    Task to search for similar embeddings in Qdrant.

    Args:
        query_text: Text to search for
        provider: Embedding provider
        model_id: Model identifier
        credential: Dictionary containing API keys
        user_id: Optional filter by user
        file_id: Optional filter by file
        limit: Number of results to return

    Returns:
        Dictionary with search results
    """
    try:
        logger.info(
            "Starting similarity search",
            query_text=query_text[:100] + "..." if len(query_text) > 100 else query_text,
            provider=provider,
            model_id=model_id,
            user_id=user_id,
            file_id=file_id,
            limit=limit
        )

        # 1. Get embedder and create query vector
        embedder = EmbedderRegistry.get_embedder(provider, model_id, credential)
        query_vector = embedder.embed_query(query_text)

        # 2. Search in Qdrant
        qdrant = QdrantService()
        search_results = qdrant.search_similar(
            query_vector=query_vector,
            user_id=user_id,
            file_id=file_id,
            limit=limit
        )

        result = {
            "status": "success",
            "query_text": query_text,
            "results_count": len(search_results),
            "results": search_results,
        }

        logger.info("Similarity search completed", **result)
        return result

    except Exception as e:
        error_result = {
            "status": "error",
            "query_text": query_text,
            "error_message": str(e),
            "error_type": type(e).__name__,
        }

        logger.error("Similarity search failed", **error_result)
        return error_result


@shared_task(name="tasks.embedding.delete_file_embeddings")
def delete_file_embeddings(user_id: str, file_id: str) -> Dict[str, Any]:
    """
    Task to delete all embeddings for a specific file.

    Args:
        user_id: User identifier
        file_id: File identifier

    Returns:
        Dictionary with deletion status
    """
    try:
        logger.info(
            "Starting file embeddings deletion",
            user_id=user_id,
            file_id=file_id
        )

        qdrant = QdrantService()
        delete_result = qdrant.delete_by_file(user_id, file_id)

        result = {
            "status": "success",
            "user_id": user_id,
            "file_id": file_id,
            "qdrant_operation": delete_result,
        }

        logger.info("File embeddings deleted successfully", **result)
        return result

    except Exception as e:
        error_result = {
            "status": "error",
            "user_id": user_id,
            "file_id": file_id,
            "error_message": str(e),
            "error_type": type(e).__name__,
        }

        logger.error("File embeddings deletion failed", **error_result)
        return error_result


@shared_task(name="tasks.embedding.delete_model")
def delete_embedding_model(model_id: str) -> Dict[str, Any]:
    """
    Task to delete a cached embedding model instance.

    Args:
        model_id: The model identifier to delete

    Returns:
        Dictionary with deletion result
    """
    try:
        logger.info(
            "Deleting embedding model from cache",
            model_id=model_id
        )

        deleted = EmbedderRegistry.delete_embedder(model_id)

        result = {
            "status": "success",
            "model_id": model_id,
            "deleted": deleted,
            "message": f"Model {model_id} deleted from cache" if deleted else f"Model {model_id} not found in cache"
        }

        logger.info("Embedding model deletion completed", **result)
        return result

    except Exception as e:
        error_result = {
            "status": "error",
            "model_id": model_id,
            "error_message": str(e),
            "error_type": type(e).__name__,
        }

        logger.error("Embedding model deletion failed", **error_result)
        return error_result


@shared_task(name="tasks.embedding.cleanup_old_models")
def cleanup_old_embedding_models(max_age_seconds: int = 3600) -> Dict[str, Any]:
    """
    Task to cleanup old embedding model instances that haven't been used recently.

    Args:
        max_age_seconds: Maximum age in seconds (default: 1 hour)

    Returns:
        Dictionary with cleanup result
    """
    try:
        logger.info(
            "Cleaning up old embedding models",
            max_age_seconds=max_age_seconds
        )

        deleted_count = EmbedderRegistry.cleanup_old_embedders(max_age_seconds)

        result = {
            "status": "success",
            "deleted_count": deleted_count,
            "max_age_seconds": max_age_seconds,
            "message": f"Cleaned up {deleted_count} old embedding models"
        }

        logger.info("Embedding model cleanup completed", **result)
        return result

    except Exception as e:
        error_result = {
            "status": "error",
            "max_age_seconds": max_age_seconds,
            "error_message": str(e),
            "error_type": type(e).__name__,
        }

        logger.error("Embedding model cleanup failed", **error_result)
        return error_result


@shared_task(name="tasks.embedding.get_cache_info")
def get_embedding_cache_info() -> Dict[str, Any]:
    """
    Task to get information about cached embedding models.

    Returns:
        Dictionary with cache information
    """
    try:
        cache_info = EmbedderRegistry.get_cache_info()

        result = {
            "status": "success",
            "cache_info": cache_info
        }

        logger.info("Retrieved embedding cache info", **result)
        return result

    except Exception as e:
        error_result = {
            "status": "error",
            "error_message": str(e),
            "error_type": type(e).__name__,
        }

        logger.error("Failed to get embedding cache info", **error_result)
        return error_result


# Removed duplicate tasks - consolidated into run_embedding
