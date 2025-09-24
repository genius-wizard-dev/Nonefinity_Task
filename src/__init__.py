"""
Vector Tasks - Optimized Celery tasks for vector embeddings.
"""

__version__ = "0.3.0"

# Core exports
from .config import settings
from .utils.logger import logger, get_logger

__all__ = [
    "settings",
    "logger",
    "get_logger",
    "__version__"
]
