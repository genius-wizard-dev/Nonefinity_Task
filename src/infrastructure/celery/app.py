"""
Celery application configuration for AI tasks system.
"""

from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure

from src.config.config import settings
from src.utils.logger import logger
from .routing import task_routes

# Create Celery app for AI tasks
celery_app = Celery(
    "ai_tasks_system",
    broker=f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    backend=f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/1",
)

# Import task routing configuration


# Configure Celery for AI tasks system
celery_app.conf.update(
    task_routes=task_routes,
    worker_concurrency=settings.WORKER_CONCURRENCY,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
    worker_prefetch_multiplier=1,
    task_default_queue='embeddings',
    worker_send_task_events=True,
)


@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handle task pre-run events."""
    logger.info(
        f"Starting task: {sender}",
        task_id=task_id,
        args_count=len(args) if args else 0,
        kwargs_keys=list(kwargs.keys()) if kwargs else []
    )


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Handle task post-run events."""
    logger.info(
        f"Completed task: {sender}",
        task_id=task_id,
        state=state,
        result_type=type(retval).__name__ if retval else None
    )


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """Handle task failure events."""
    logger.error(
        f"Task failed: {sender}",
        task_id=task_id,
        exception=str(exception),
        exception_type=type(exception).__name__
    )


def auto_discover_tasks():
    """Auto-discover tasks from all AI modules."""
    task_modules = [
        'src.ai.embeddings',
        'src.tasks.ai',
    ]

    celery_app.autodiscover_tasks(task_modules)




def check_redis_connection():
    """Health check for Redis connection."""
    try:
        from celery import current_app
        conn = current_app.broker_connection()
        conn.ensure_connection(max_retries=3)
        return 'Redis connection healthy'
    except Exception as e:
        return f'Redis connection failed: {e}'


# Initialize task discovery
auto_discover_tasks()
