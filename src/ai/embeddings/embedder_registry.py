import hashlib
import time
from typing import Dict, Any

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings

from src.utils.logger import logger

class EmbedderRegistry:
    """
    Registry for caching embedding models to avoid repeated initialization.
    Cache key is based on model_id for easy identification and deletion.

    Cache structure: {model_id: {embedder: instance, metadata: info}}
    """

    _cache: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def _create_cache_key(cls, model_id: str, provider: str, credential: dict) -> str:
        """
        Create a unique cache key based on model_id, provider, api_key, and base_url.

        Args:
            model_id: The model identifier (primary key)
            provider: The embedding provider
            credential: Dictionary containing API keys and base url

        Returns:
            Cache key in format: "{provider}:{model_id}:{api_key_hash}:{base_url_hash}"
        """
        api_key = credential.get("api_key", "")
        base_url = credential.get("base_url", "")
        # Use short hashes for sensitive info, empty string if not present
        api_key_hash = hashlib.md5(api_key.encode()).hexdigest()[:8] if api_key else "no_key"
        base_url_hash = hashlib.md5(base_url.encode()).hexdigest()[:8] if base_url else "no_url"
        return f"{provider}:{model_id}:{api_key_hash}:{base_url_hash}"

    @classmethod
    def get_embedder(cls, provider: str, model_id: str, credential: dict):
        """
        Get or create an embedder instance for the given configuration.

        Args:
            provider: The embedding provider (openai, huggingface, google, etc.)
            model_id: The model identifier (used as cache key)
            credential: Dictionary containing API keys and other credentials

        Returns:
            Cached or new embedder instance
        """
        cache_key = cls._create_cache_key(model_id, provider, credential)

        if cache_key not in cls._cache:
            logger.info(
                "Creating new embedder instance",
                model_id=model_id,
                provider=provider,
                cache_key=cache_key
            )

            embedder_instance = cls._create_embedder(provider, model_id, credential)

            cls._cache[cache_key] = {
                "embedder": embedder_instance,
                "metadata": {
                    "model_id": model_id,
                    "provider": provider,
                    "created_at": time.time(),
                    "last_used": time.time(),
                    "use_count": 0,
                    "api_key_hash": hashlib.md5(
                        credential.get("api_key", "").encode()
                    ).hexdigest()[:8] if credential.get("api_key") else "no_key"
                }
            }
        else:
            # Update usage stats
            cls._cache[cache_key]["metadata"]["last_used"] = time.time()
            cls._cache[cache_key]["metadata"]["use_count"] += 1

            logger.info(
                "Retrieved cached embedder",
                model_id=model_id,
                cache_key=cache_key,
                use_count=cls._cache[cache_key]["metadata"]["use_count"]
            )

        return cls._cache[cache_key]["embedder"]

    @classmethod
    def _create_embedder(cls, provider: str, model_id: str, credential: dict):
        """Create a new embedder instance based on provider."""
        print(f"Creating embedder instance for {provider} with model_id {model_id} and credential {credential}")
        if provider == "openai":
            return OpenAIEmbeddings(
                model=model_id,
                openai_api_key=credential.get("api_key"),
                base_url=credential.get("base_url"),
            )
        elif provider == "huggingface":
            return HuggingFaceEmbeddings(
                model_name=model_id,
                model_kwargs=credential.get("model_kwargs", {}),
                encode_kwargs=credential.get("encode_kwargs", {}),
                base_url=credential.get("base_url"),
            )
        elif provider == "google":
            # TODO: Add Google Embeddings adapter when available
            # from langchain_google_genai import GoogleGenerativeAIEmbeddings
            # return GoogleGenerativeAIEmbeddings(
            #     model=model_id,
            #     google_api_key=credential.get("api_key"),
            # )
            raise NotImplementedError("Google embedding chưa được implement")
        else:
            raise ValueError(f"Unknown provider: {provider}")

    @classmethod
    def delete_embedder(cls, model_id: str) -> bool:
        """
        Delete a cached embedder instance by model_id.

        Args:
            model_id: The model identifier to delete

        Returns:
            True if embedder was deleted, False if not found
        """
        cache_key = model_id  # model_id is the cache key

        if cache_key in cls._cache:
            metadata = cls._cache[cache_key]["metadata"]
            logger.info(
                "Deleting cached embedder",
                model_id=model_id,
                provider=metadata["provider"],
                use_count=metadata["use_count"],
                cache_duration_seconds=time.time() - metadata["created_at"]
            )

            del cls._cache[cache_key]
            return True
        else:
            logger.warning(
                "Attempted to delete non-existent embedder",
                model_id=model_id
            )
            return False

    @classmethod
    def get_cache_info(cls) -> dict:
        """Get information about cached embedders."""
        cache_info = {
            "total_cached_embedders": len(cls._cache),
            "embedders": {}
        }

        for cache_key, cache_data in cls._cache.items():
            metadata = cache_data["metadata"]
            cache_info["embedders"][cache_key] = {
                "model_id": metadata["model_id"],
                "provider": metadata["provider"],
                "created_at": metadata["created_at"],
                "last_used": metadata["last_used"],
                "use_count": metadata["use_count"],
                "api_key_hash": metadata["api_key_hash"],
                "age_seconds": time.time() - metadata["created_at"]
            }

        return cache_info

    @classmethod
    def cleanup_old_embedders(cls, max_age_seconds: int = 3600) -> int:
        """
        Clean up embedders that haven't been used for a specified time.

        Args:
            max_age_seconds: Maximum age in seconds (default: 1 hour)

        Returns:
            Number of embedders cleaned up
        """
        current_time = time.time()
        keys_to_delete = []

        for cache_key, cache_data in cls._cache.items():
            last_used = cache_data["metadata"]["last_used"]
            if (current_time - last_used) > max_age_seconds:
                keys_to_delete.append(cache_key)

        deleted_count = 0
        for key in keys_to_delete:
            if cls.delete_embedder(key):
                deleted_count += 1

        logger.info(
            "Cleaned up old embedders",
            deleted_count=deleted_count,
            max_age_seconds=max_age_seconds
        )

        return deleted_count
