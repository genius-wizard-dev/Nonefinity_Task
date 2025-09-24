# Vector Tasks - Optimized Embedding System

Simplified Celery-based task system focused on creating and managing embeddings with multiple providers (OpenAI, HuggingFace) and vector database integration.

## 🚀 Quick Start (3 bước)

### 1. Setup Environment

```bash
# Copy và edit config
cp .env.sample .env
# Thêm API keys vào .env
```

### 2. Start Services

```bash
# Start Redis + Qdrant (required)
docker-compose -f docker-compose.simple.yml up -d

# Hoặc manual:
# redis-server --requirepass sapassword
# docker run -p 6333:6333 qdrant/qdrant
```

### 3. Run Worker

```bash
# Đơn giản nhất
python run.py worker

# Hoặc trực tiếp
python worker.py

# Monitor (optional)
python run.py flower
```

## 🧪 Test

```bash
# Test by calling embedding task directly
python -c "from src.tasks.ai.embedding import run_embedding; print('✅ Tasks imported successfully')"
```

## 📊 Usage Example

````python
from src.tasks.ai.embedding import run_embedding

# Create embeddings from text chunks
result = run_embedding.delay(
    user_id="user123",
    chunks=["Text chunk 1", "Text chunk 2"],
    provider="openai",
    model_id="text-embedding-ada-002",
    credential={"api_key": "sk-..."}
)

# Or create embeddings from file
result = run_embedding.delay(
    user_id="user123",
    file_id="doc456",
    provider="openai",
    model_id="text-embedding-ada-002",
    credential={"api_key": "sk-..."},
    split_config={"chunk_size": 1000, "chunk_overlap": 200}
)

print(result.get())
```### Supported Providers

#### OpenAI

```python
{
    "provider": "openai",
    "model_id": "text-embedding-ada-002",
    "credential": {"api_key": "sk-..."}
}
````

#### HuggingFace

```python
{
    "provider": "huggingface",
    "model_id": "sentence-transformers/all-MiniLM-L6-v2",
    "credential": {
        "model_kwargs": {"device": "cpu"},
        "encode_kwargs": {"normalize_embeddings": True}
    }
}
```

#### Google (Not Implemented)

Google embedding support has been removed for simplicity.

## Testing

```bash
# Test OpenAI embeddings
python test_tasks.py

# Test HuggingFace embeddings
python test_tasks.py hf

# Run with your API keys in .env
```

## Architecture (Optimized)

```
src/
├── core/
│   ├── celery.py              # Simplified Celery config
│   └── embedder_registry.py   # Provider caching
├── database/
│   ├── mongodb.py             # Async MongoDB client
│   ├── qdrant_service.py      # Vector database operations
│   ├── minio_service.py       # File storage operations
│   └── constants.py           # Database constants
├── tasks/
│   └── ai/
│       └── embedding.py       # Unified embedding tasks
└── utils/
    ├── logger.py              # Structured logging
    └── text_processor.py      # LangChain text processing
```

## Task Types

### 1. `run_embedding` (Unified)

Creates embeddings from text chunks OR files and stores in Qdrant

- Handles both text chunks and file processing
- Caches embedders per provider/model
- Handles retries on failure
- Structured logging
- Supports LangChain document processing

### 2. `search_similar`

Finds similar content using vector search

- Embeds query text
- Searches Qdrant with filters
- Returns ranked results

### 3. `delete_file_embeddings`

Removes all embeddings for a file

- Cleans up Qdrant vectors
- Supports user/file filtering

### 4. Cache Management Tasks

- `delete_embedding_model`: Remove cached embedder
- `cleanup_old_embedding_models`: Remove unused cached embedders
- `get_embedding_cache_info`: Get cache statistics

## Configuration

### Environment Variables

```bash
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=sapassword

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=optional_api_key
QDRANT_COLLECTION=embeddings_collection

# MongoDB
MONGO_URI=mongodb://user:password@localhost:27017
MONGO_DB=my_database

# Worker
WORKER_CONCURRENCY=4
```

### Embedder Caching

The system caches embedder instances using:

```
{provider}:{model_id}:{api_key_hash}
```

This prevents re-initialization of expensive embedding models and improves performance.

## Monitoring

- **Flower**: http://localhost:5555 (task monitoring)
- **Qdrant Dashboard**: http://localhost:6333/dashboard
- **Logs**: Structured JSON logs with task metrics

## Scaling

```bash
# Scale workers
docker-compose up -d --scale worker=5

# Single embeddings queue only
celery -A src.core.celery worker -Q embeddings

# Monitor queue sizes
celery -A src.core.celery inspect active_queues
```

## Development

```bash
# Install dependencies
uv sync

# Format code
black src/
ruff check src/

# Run worker
python worker.py
```
