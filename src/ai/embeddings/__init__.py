"""
AI Embeddings module for vector embedding tasks.
"""

from .embedder_registry import EmbedderRegistry
from .embedding import (
    run_embedding,
    search_similar,
    delete_file_embeddings,
    delete_embedding_model,
    cleanup_old_embedding_models,
    get_embedding_cache_info
)

__all__ = [
    # Model registry
    "EmbedderRegistry",

    # Embedding tasks
    "run_embedding",
    "search_similar",
    "delete_file_embeddings",
    "delete_embedding_model",
    "cleanup_old_embedding_models",
    "get_embedding_cache_info"
]
