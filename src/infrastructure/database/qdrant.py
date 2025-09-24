import uuid
from typing import List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from src.config.config import settings


class QdrantService:
    """Service for managing Qdrant vector database operations."""

    def __init__(self):
        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            api_key=settings.QDRANT_API_KEY,
            https=False,  # Disable SSL since the server is running on HTTP
        )
        self.collection = settings.QDRANT_COLLECTION

    def ensure_collection_exists(self, vector_size: int = 1536):
        """Create collection if it doesn't exist."""
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]

            if self.collection not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
                )
        except Exception as e:
            print(f"Error ensuring collection exists: {e}")

    def save_embeddings(
        self,
        user_id: str,
        file_id: str,
        chunks: List[str],
        vectors: List[List[float]]
    ) -> Dict[str, Any]:
        """
        Save text chunks and their embeddings to Qdrant.

        Args:
            user_id: User identifier
            file_id: File identifier
            chunks: List of text chunks
            vectors: List of embedding vectors

        Returns:
            Dictionary with operation status and metadata
        """
        if len(chunks) != len(vectors):
            raise ValueError("Number of chunks must match number of vectors")

        # Ensure collection exists with proper vector size
        if vectors:
            vector_size = len(vectors[0])
            self.ensure_collection_exists(vector_size)

        points = []
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
            point_id = str(uuid.uuid4())
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "user_id": user_id,
                        "file_id": file_id,
                        "chunk_index": idx,
                        "text": chunk,
                        "created_at": "2025-09-21T00:00:00Z",  # Could use datetime.utcnow().isoformat()
                    }
                )
            )

        # Upsert points to Qdrant
        operation_info = self.client.upsert(
            collection_name=self.collection,
            points=points
        )

        return {
            "status": "success",
            "points_processed": len(points),
            "operation_id": operation_info.operation_id,
        }

    def search_similar(
        self,
        query_vector: List[float],
        user_id: str = None,
        file_id: str = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in the collection.

        Args:
            query_vector: Vector to search for
            user_id: Optional filter by user_id
            file_id: Optional filter by file_id
            limit: Number of results to return

        Returns:
            List of search results with scores and metadata
        """
        filter_conditions = {}
        if user_id:
            filter_conditions["user_id"] = user_id
        if file_id:
            filter_conditions["file_id"] = file_id

        search_results = self.client.search(
            collection_name=self.collection,
            query_vector=query_vector,
            query_filter=filter_conditions if filter_conditions else None,
            limit=limit,
        )

        return [
            {
                "id": result.id,
                "score": result.score,
                "text": result.payload.get("text"),
                "metadata": result.payload,
            }
            for result in search_results
        ]

    def delete_by_file(self, user_id: str, file_id: str) -> Dict[str, Any]:
        """Delete all vectors for a specific file."""
        filter_conditions = {
            "user_id": user_id,
            "file_id": file_id,
        }

        operation_info = self.client.delete(
            collection_name=self.collection,
            points_selector=filter_conditions,
        )

        return {
            "status": "success",
            "operation_id": operation_info.operation_id,
        }

    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection."""
        try:
            info = self.client.get_collection(self.collection)
            return {
                "status": "success",
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
            }
