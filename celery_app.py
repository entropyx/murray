from celery import Celery
from dotenv import load_dotenv
import os
import redis
import logging
load_dotenv()

REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_DB = os.getenv("REDIS_DB", "0")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

redis_client = redis.Redis.from_url(CELERY_BROKER_URL)
celery_app = Celery(
    "murray_tasks",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_send_task_events=True,
    task_send_sent_event=True,
    task_ignore_result=False,
    result_expires=86400,  # Keep results for 24 hours
    task_soft_time_limit=7200,  # 2 hours soft limit
    task_time_limit=10800,  # 3 hours hard limit
    worker_prefetch_multiplier=1,  # Process one task at a time for better progress tracking
)

logger = logging.getLogger(__name__)