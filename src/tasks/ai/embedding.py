"""
Compatibility module for task imports.
This module provides backward compatibility for the expected import structure.
"""

# Import all tasks from the actual implementation
from src.ai.embeddings.embedding import (
    run_embedding,
    search_similar,
    delete_file_embeddings,
    delete_embedding_model,
    cleanup_old_embedding_models,
    get_embedding_cache_info
)

# Make all tasks available at this module level
__all__ = [
    'run_embedding',
    'search_similar',
    'delete_file_embeddings',
    'delete_embedding_model',
    'cleanup_old_embedding_models',
    'get_embedding_cache_info'
]
