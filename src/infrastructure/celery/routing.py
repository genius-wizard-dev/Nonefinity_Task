"""
Task routing configuration for the AI tasks system.
"""

# Task routing rules for different queues
task_routes = {
    # AI Embedding tasks
    "tasks.embedding.*": {
        "queue": "embeddings",
        "routing_key": "embeddings"
    },
    # Legacy AI Embedding tasks (for backward compatibility)
    "ai.embeddings.*": {
        "queue": "embeddings",
        "routing_key": "embeddings"
    },

    # Default queue for unmatched tasks
    "*": {
        "queue": "embeddings",
        "routing_key": "default"
    }

}

# Queue definitions with priorities
QUEUE_PRIORITIES = {
    "embeddings": 7,   # High priority for embeddings
}

# Queue configurations
QUEUE_CONFIGS = {
    "embeddings": {
        "routing_key": "embeddings",
        "max_retries": 3,
        "default_retry_delay": 60,
    },
}
