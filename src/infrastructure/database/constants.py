"""
MongoDB collection constants for easy reference
"""


class Collections:
    """Constants for MongoDB collection names"""
    FILES = "files"
    EMBEDDINGS = "embeddings"


class FileFields:
    """Constants for file document fields used in current operations"""
    ID = "_id"
    OWNER_ID = "owner_id"
    FILE_NAME = "file_name"
    FILE_TYPE = "file_type"
    FILE_SIZE = "file_size"
