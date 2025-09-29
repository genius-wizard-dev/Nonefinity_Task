"""
LangChain-based text processing utilities for extracting text from different file types
"""

from pathlib import Path
from typing import List, Dict, Any, Optional

from langchain.schema import Document
from langchain_community.document_loaders import (
    TextLoader, CSVLoader, JSONLoader, UnstructuredMarkdownLoader, PyPDFLoader,
    Docx2txtLoader, UnstructuredExcelLoader, UnstructuredPowerPointLoader,
    UnstructuredHTMLLoader, UnstructuredXMLLoader
)
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter, CharacterTextSplitter, TokenTextSplitter
)

from src.infrastructure.storage import MinioService
from src.utils.logger import logger


class LangChainTextProcessor:
    """LangChain-based text processor for various file formats"""

    def __init__(self):
        self.minio_service = MinioService()

        # Default splitter configuration
        self.default_splitter_config = {
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "separators": ["\n\n", "\n", " ", ""]
        }

    def process_file_content(
        self,
        content: bytes,
        file_type: str,
        file_name: str = "",
        split_config: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Process file content using LangChain document loaders

        Args:
            content: File content as bytes
            file_type: MIME type of the file
            file_name: Original file name
            split_config: Configuration for text splitting

        Returns:
            List of LangChain Document objects
        """
        try:
            logger.info(
                "Processing file content with LangChain",
                file_type=file_type,
                file_name=file_name,
                content_size=len(content)
            )

            # Create temporary file for LangChain loaders
            file_suffix = self._get_file_suffix(file_type, file_name)
            temp_path = self.minio_service.create_temp_file(content, suffix=file_suffix)

            try:
                # Load documents using appropriate LangChain loader
                documents = self._load_documents_by_type(temp_path, file_type, file_name)

                # Apply text splitting if needed
                if split_config or len(str(documents)) > 2000:
                    documents = self._split_documents(documents, split_config)

                logger.info(
                    "File processed successfully with LangChain",
                    file_name=file_name,
                    documents_count=len(documents),
                    total_chars=sum(len(doc.page_content) for doc in documents)
                )

                return documents

            finally:
                # Clean up temporary file
                self.minio_service.cleanup_temp_file(temp_path)

        except Exception as e:
            logger.error(
                "Error processing file content with LangChain",
                file_type=file_type,
                file_name=file_name,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise

    def _load_documents_by_type(self, file_path: str, file_type: str, file_name: str) -> List[Document]:
        """Load documents using appropriate LangChain loader based on file type"""

        try:
            if file_type == "text/plain":
                loader = TextLoader(file_path, encoding='utf-8')

            elif file_type == "text/csv":
                loader = CSVLoader(file_path)

            elif file_type == "application/json":
                # JSONLoader requires jq_schema for complex JSON
                loader = JSONLoader(
                    file_path=file_path,
                    jq_schema='.',
                    text_content=False
                )

            elif file_type == "text/markdown":
                loader = UnstructuredMarkdownLoader(file_path)

            elif file_type == "application/pdf":
                loader = PyPDFLoader(file_path)

            elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                loader = Docx2txtLoader(file_path)

            elif file_type in [
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/vnd.ms-excel"
            ]:
                loader = UnstructuredExcelLoader(file_path)

            elif file_type in [
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                "application/vnd.ms-powerpoint"
            ]:
                loader = UnstructuredPowerPointLoader(file_path)

            elif file_type == "text/html":
                loader = UnstructuredHTMLLoader(file_path)

            elif file_type in ["application/xml", "text/xml"]:
                loader = UnstructuredXMLLoader(file_path)

            else:
                logger.warning(
                    "Unsupported file type, using TextLoader as fallback",
                    file_type=file_type,
                    file_name=file_name
                )
                loader = TextLoader(file_path, encoding='utf-8')

            # Load documents
            documents = loader.load()

            # Add metadata
            for doc in documents:
                doc.metadata.update({
                    "source_file": file_name,
                    "file_type": file_type,
                    "processed_with": "langchain"
                })

            logger.info(
                "Documents loaded successfully",
                loader_type=type(loader).__name__,
                documents_count=len(documents)
            )

            return documents

        except Exception as e:
            logger.error(
                "Error loading documents",
                file_path=file_path,
                file_type=file_type,
                loader_type=type(loader).__name__ if 'loader' in locals() else "unknown",
                error_message=str(e)
            )
            raise

    def _split_documents(
        self,
        documents: List[Document],
        split_config: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """Split documents using LangChain text splitters"""

        if not split_config:
            split_config = self.default_splitter_config

        try:
            # Choose splitter based on configuration
            splitter_type = split_config.get("type", "recursive")

            if splitter_type == "recursive":
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=split_config.get("chunk_size", 1000),
                    chunk_overlap=split_config.get("chunk_overlap", 200),
                    separators=split_config.get("separators", ["\n\n", "\n", " ", ""])
                )
            elif splitter_type == "character":
                splitter = CharacterTextSplitter(
                    chunk_size=split_config.get("chunk_size", 1000),
                    chunk_overlap=split_config.get("chunk_overlap", 200),
                    separator=split_config.get("separator", "\n\n")
                )
            elif splitter_type == "token":
                splitter = TokenTextSplitter(
                    chunk_size=split_config.get("chunk_size", 1000),
                    chunk_overlap=split_config.get("chunk_overlap", 200)
                )
            else:
                # Default to recursive
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=split_config.get("chunk_size", 1000),
                    chunk_overlap=split_config.get("chunk_overlap", 200)
                )

            # Split documents
            split_documents = splitter.split_documents(documents)

            # Add chunk metadata
            for i, doc in enumerate(split_documents):
                doc.metadata.update({
                    "chunk_index": i,
                    "splitter_type": splitter_type,
                    "chunk_size": split_config.get("chunk_size", 1000),
                    "chunk_overlap": split_config.get("chunk_overlap", 200)
                })

            logger.info(
                "Documents split successfully",
                original_docs=len(documents),
                split_docs=len(split_documents),
                splitter_type=splitter_type,
                chunk_size=split_config.get("chunk_size", 1000)
            )

            return split_documents

        except Exception as e:
            logger.error(
                "Error splitting documents",
                documents_count=len(documents),
                split_config=split_config,
                error_message=str(e)
            )
            raise

    def _get_file_suffix(self, file_type: str, file_name: str) -> str:
        """Get appropriate file suffix for temporary file"""

        # Try to get suffix from file name first
        if file_name and "." in file_name:
            return Path(file_name).suffix

        # Map MIME types to file extensions
        mime_to_suffix = {
            "text/plain": ".txt",
            "text/csv": ".csv",
            "application/json": ".json",
            "text/markdown": ".md",
            "application/pdf": ".pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
            "application/vnd.ms-excel": ".xls",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
            "application/vnd.ms-powerpoint": ".ppt",
            "text/html": ".html",
            "application/xml": ".xml",
            "text/xml": ".xml"
        }

        return mime_to_suffix.get(file_type, ".txt")

    def extract_text_chunks(self, documents: List[Document]) -> List[str]:
        """
        Extract text chunks from LangChain documents for backward compatibility

        Args:
            documents: List of LangChain Document objects

        Returns:
            List of text strings
        """
        return [doc.page_content for doc in documents if doc.page_content.strip()]

    def get_supported_file_types(self) -> List[str]:
        """Get list of supported file types"""
        return [
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
            "text/xml"
        ]

    def is_supported_file_type(self, file_type: str) -> bool:
        """Check if file type is supported"""
        return file_type in self.get_supported_file_types()


# Factory function for creating text processor
def create_text_processor():
    """
    Factory function to create text processor

    Returns:
        LangChain-based text processor instance
    """
    return LangChainTextProcessor()
