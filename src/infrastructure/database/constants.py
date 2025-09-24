"""
MongoDB collection constants for easy reference
"""

# MongoDB Collection Names
class Collections:
    """Constants for MongoDB collection names"""
    FILES = "files"
    USERS = "users"
    EMBEDDINGS = "embeddings"
    CONVERSATIONS = "conversations"
    CHAT_SESSIONS = "chat_sessions"
    MODELS = "models"
    CREDENTIALS = "credentials"
    WORKFLOWS = "workflows"


# MongoDB Field Names for common operations
class FileFields:
    """Constants for file document fields"""
    ID = "_id"
    OWNER_ID = "owner_id"
    BUCKET = "bucket"
    FILE_PATH = "file_path"
    FILE_NAME = "file_name"
    FILE_EXT = "file_ext"
    FILE_TYPE = "file_type"
    FILE_SIZE = "file_size"
    URL = "url"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class UserFields:
    """Constants for user document fields"""
    ID = "_id"
    EMAIL = "email"
    USERNAME = "username"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class EmbeddingFields:
    """Constants for embedding document fields"""
    ID = "_id"
    FILE_ID = "file_id"
    USER_ID = "user_id"
    CHUNK_INDEX = "chunk_index"
    CHUNK_TEXT = "chunk_text"
    VECTOR_ID = "vector_id"  # Qdrant point ID
    PROVIDER = "provider"
    MODEL_ID = "model_id"
    CREATED_AT = "created_at"


# Minio related constants
class MinioConstants:
    """Constants for Minio operations"""
    DEFAULT_EXPIRY = 604800  # 7 days in seconds
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

    # Supported file types for embedding (LangChain supported)
    SUPPORTED_TEXT_TYPES = [
        "text/plain",
        "text/csv",
        "application/json",
        "text/markdown",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
        "application/vnd.ms-excel",  # .xls
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
        "application/vnd.ms-powerpoint",  # .ppt
        "text/html",
        "application/xml",
        "text/xml",
    ]

    CHUNK_SIZE = 8192  # 8KB chunks for file reading
