import os
import tempfile
from typing import Optional, Dict, Any, BinaryIO
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error

from src.config.config import settings
from src.infrastructure.database.constants import MinioConstants
from src.utils.logger import logger


class MinioService:
    """Service for Minio file operations"""

    def __init__(self):
        """Initialize Minio client"""
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )

        logger.info(
            "Minio client initialized",
            endpoint=settings.MINIO_ENDPOINT,
            secure=settings.MINIO_SECURE
        )

    def download_file_by_url(self, file_url: str) -> bytes:
        """
        Download file content by presigned URL

        Args:
            file_url: Presigned URL from file document

        Returns:
            File content as bytes
        """
        try:
            # Parse URL to extract bucket and object path
            parsed_url = urlparse(file_url)
            path_parts = parsed_url.path.strip('/').split('/')

            if len(path_parts) < 2:
                raise ValueError("Invalid file URL format")

            bucket = path_parts[0]
            object_path = '/'.join(path_parts[1:])

            logger.info(
                "Downloading file from Minio",
                bucket=bucket,
                object_path=object_path,
                url=file_url[:100] + "..." if len(file_url) > 100 else file_url
            )

            # Download file content
            response = self.client.get_object(bucket, object_path)
            content = response.read()
            response.close()
            response.release_conn()

            logger.info(
                "File downloaded successfully",
                bucket=bucket,
                object_path=object_path,
                content_size=len(content)
            )

            return content

        except S3Error as e:
            logger.error(
                "Minio S3 error while downloading file",
                error_code=e.code,
                error_message=str(e),
                file_url=file_url[:100] + "..." if len(file_url) > 100 else file_url
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error while downloading file",
                error_type=type(e).__name__,
                error_message=str(e),
                file_url=file_url[:100] + "..." if len(file_url) > 100 else file_url
            )
            raise

    def download_file_by_path(self, bucket: str, object_path: str) -> bytes:
        """
        Download file content by bucket and path

        Args:
            bucket: Minio bucket name
            object_path: Object path in bucket

        Returns:
            File content as bytes
        """
        try:
            logger.info(
                "Downloading file from Minio by path",
                bucket=bucket,
                object_path=object_path
            )

            response = self.client.get_object(bucket, object_path)
            content = response.read()
            response.close()
            response.release_conn()

            logger.info(
                "File downloaded successfully by path",
                bucket=bucket,
                object_path=object_path,
                content_size=len(content)
            )

            return content

        except S3Error as e:
            logger.error(
                "Minio S3 error while downloading file by path",
                error_code=e.code,
                error_message=str(e),
                bucket=bucket,
                object_path=object_path
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error while downloading file by path",
                error_type=type(e).__name__,
                error_message=str(e),
                bucket=bucket,
                object_path=object_path
            )
            raise

    def get_file_stream(self, bucket: str, object_path: str) -> BinaryIO:
        """
        Get file as stream for large files

        Args:
            bucket: Minio bucket name
            object_path: Object path in bucket

        Returns:
            File stream
        """
        try:
            logger.info(
                "Getting file stream from Minio",
                bucket=bucket,
                object_path=object_path
            )

            response = self.client.get_object(bucket, object_path)
            return response

        except S3Error as e:
            logger.error(
                "Minio S3 error while getting file stream",
                error_code=e.code,
                error_message=str(e),
                bucket=bucket,
                object_path=object_path
            )
            raise

    def check_file_exists(self, bucket: str, object_path: str) -> bool:
        """
        Check if file exists in Minio

        Args:
            bucket: Minio bucket name
            object_path: Object path in bucket

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.client.stat_object(bucket, object_path)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            raise
        except Exception:
            return False

    def get_file_info(self, bucket: str, object_path: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata from Minio

        Args:
            bucket: Minio bucket name
            object_path: Object path in bucket

        Returns:
            Dictionary with file metadata or None if not found
        """
        try:
            stat = self.client.stat_object(bucket, object_path)

            return {
                "bucket": bucket,
                "object_path": object_path,
                "size": stat.size,
                "etag": stat.etag,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified,
                "metadata": stat.metadata
            }

        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.warning(
                    "File not found in Minio",
                    bucket=bucket,
                    object_path=object_path
                )
                return None
            raise
        except Exception as e:
            logger.error(
                "Error getting file info from Minio",
                error_type=type(e).__name__,
                error_message=str(e),
                bucket=bucket,
                object_path=object_path
            )
            raise

    def create_temp_file(self, content: bytes, suffix: str = None) -> str:
        """
        Create temporary file from content

        Args:
            content: File content as bytes
            suffix: File suffix (e.g., '.csv', '.pdf')

        Returns:
            Path to temporary file
        """
        try:
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix
            )
            temp_file.write(content)
            temp_file.close()

            logger.info(
                "Created temporary file",
                temp_path=temp_file.name,
                content_size=len(content),
                suffix=suffix
            )

            return temp_file.name

        except Exception as e:
            logger.error(
                "Error creating temporary file",
                error_type=type(e).__name__,
                error_message=str(e),
                content_size=len(content),
                suffix=suffix
            )
            raise

    def cleanup_temp_file(self, temp_path: str):
        """
        Clean up temporary file

        Args:
            temp_path: Path to temporary file
        """
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                logger.info("Cleaned up temporary file", temp_path=temp_path)
        except Exception as e:
            logger.warning(
                "Failed to cleanup temporary file",
                temp_path=temp_path,
                error_message=str(e)
            )

    @staticmethod
    def extract_bucket_and_path_from_url(file_url: str) -> tuple[str, str]:
        """
        Extract bucket and object path from file URL

        Args:
            file_url: Full file URL

        Returns:
            Tuple of (bucket, object_path)
        """
        try:
            parsed_url = urlparse(file_url)
            path_parts = parsed_url.path.strip('/').split('/')

            if len(path_parts) < 2:
                raise ValueError("Invalid file URL format")

            bucket = path_parts[0]
            object_path = '/'.join(path_parts[1:])

            return bucket, object_path

        except Exception as e:
            logger.error(
                "Error extracting bucket and path from URL",
                error_message=str(e),
                file_url=file_url[:100] + "..." if len(file_url) > 100 else file_url
            )
            raise ValueError(f"Invalid file URL: {str(e)}")

    def is_supported_file_type(self, file_type: str) -> bool:
        """
        Check if file type is supported for embedding

        Args:
            file_type: MIME type of the file

        Returns:
            True if supported, False otherwise
        """
        return file_type in MinioConstants.SUPPORTED_TEXT_TYPES
