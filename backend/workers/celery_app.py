"""
Celery application configuration
Task queue for background processing (video AI pipeline)
"""
from celery import Celery
from celery.schedules import crontab
import os

from core.config import settings

# Initialize Celery app
celery_app = Celery(
    "english_video_learning",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "workers.video_pipeline",
        "workers.stt_task",
        "workers.chunking_task",
        "workers.translation_task",
        "workers.indexing_task",
        "workers.clip_task",
        "workers.ffmpeg_task",
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3000,  # 50 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (prevent memory leaks)
)

# Periodic tasks (Celery Beat schedule)
celery_app.conf.beat_schedule = {
    # Clean up old clips daily at 2 AM
    'cleanup-old-clips': {
        'task': 'workers.clip_task.cleanup_old_clips',
        'schedule': crontab(hour=2, minute=0),
    },
    # Reset daily quotas at midnight
    'reset-daily-quotas': {
        'task': 'workers.clip_task.reset_daily_quotas',
        'schedule': crontab(hour=0, minute=0),
    },
}

# Task routes (queue assignment)
celery_app.conf.task_routes = {
    'workers.video_pipeline.*': {'queue': 'video_processing'},
    'workers.stt_task.*': {'queue': 'ai_tasks'},
    'workers.chunking_task.*': {'queue': 'ai_tasks'},
    'workers.translation_task.*': {'queue': 'ai_tasks'},
    'workers.indexing_task.*': {'queue': 'indexing'},
    'workers.clip_task.*': {'queue': 'clip_processing'},
    'workers.ffmpeg_task.*': {'queue': 'video_processing'},
}

# Default queue
celery_app.conf.task_default_queue = 'default'

# Retry policy
celery_app.conf.task_default_retry_delay = 60  # Retry after 1 minute
celery_app.conf.task_max_retries = 3

print("✅ Celery app configured successfully")
