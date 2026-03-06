"""Celery application configuration with Redis broker and result backend."""

from __future__ import annotations

from celery import Celery

from app.core.config import settings

# ---------------------------------------------------------------------------
# Celery application factory
# ---------------------------------------------------------------------------
celery_app = Celery(
    "appr",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        # Register task modules here as they are added:
        # "app.tasks.scorecard_tasks",
        # "app.tasks.sync_tasks",
    ],
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
celery_app.conf.update(
    # Serialisation
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task result TTL (24 hours)
    result_expires=86_400,
    # Retry behaviour
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,
    task_max_retries=3,
    # Visibility timeout (must be >= longest task duration)
    broker_transport_options={
        "visibility_timeout": 3600,
    },
    # Worker concurrency – adjust per environment
    worker_concurrency=4,
    worker_prefetch_multiplier=1,
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    # Beat schedule placeholder
    beat_schedule={},
    # Redis result backend options
    redis_max_connections=20,
    result_backend_transport_options={
        "master_name": None,  # Set for Redis Sentinel deployments
    },
)

__all__ = ["celery_app"]
