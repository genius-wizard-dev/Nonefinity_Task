from pydantic_settings import BaseSettings
from pydantic import field_validator, ValidationError
import sys


class Settings(BaseSettings):
    # Redis
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str

    # Qdrant
    QDRANT_HOST: str
    QDRANT_PORT: int
    QDRANT_API_KEY: str | None = None
    QDRANT_COLLECTION: str

    # MongoDB
    MONGO_URI: str
    MONGO_DB: str

    # Minio
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_SECURE: bool = False

    # Worker
    WORKER_CONCURRENCY: int = 2

    @field_validator('REDIS_PORT', 'QDRANT_PORT')
    @classmethod
    def validate_ports(cls, v):
        if not (1 <= v <= 65535):
            raise ValueError('Port must be between 1 and 65535')
        return v

    @field_validator('WORKER_CONCURRENCY')
    @classmethod
    def validate_concurrency(cls, v):
        if v < 1:
            raise ValueError('Worker concurrency must be at least 1')
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


def load_settings() -> Settings:
    """Load settings with error handling and validation."""
    try:
        return Settings()
    except ValidationError as e:
        missing_fields = []
        for error in e.errors():
            if error['type'] == 'missing':
                field_name = '.'.join(str(loc) for loc in error['loc'])
                missing_fields.append(field_name)

        if missing_fields:
            print(f"❌ Missing required environment variables: {', '.join(missing_fields)}")
            print("Please check your .env file and ensure all required variables are set.")
        else:
            print(f"❌ Configuration validation error: {e}")

        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        sys.exit(1)


settings = load_settings()
