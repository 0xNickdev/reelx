from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "reelx",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.services.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_max_tasks_per_child=10,  # restart worker after 10 tasks (memory leak prevention)
    task_time_limit=600,            # 10 min hard limit per task
    task_soft_time_limit=540,       # 9 min soft limit
)
