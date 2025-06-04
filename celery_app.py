from celery import Celery
from dotenv import load_dotenv
import os
import redis
from celery.signals import task_prerun, task_postrun, task_failure
import requests
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
)

logger = logging.getLogger(__name__)

def notify_webhook(task_id, status, results=None, error=None):
    webhook_url = redis_client.get(f"webhook:{task_id}")
    if webhook_url:
        try:
            payload = {
                "task_id": task_id,
                "status": status,
                "results": results,
                "error": error,
            }
            requests.post(webhook_url.decode(), json=payload, timeout=5)
        except Exception as ex:
            logger.error(f"[{task_id}] Error sending webhook: {ex}")

@task_prerun.connect
def task_started_handler(sender=None, task_id=None, **kwargs):
    notify_webhook(task_id, "STARTED")

@task_postrun.connect
def task_completed_handler(sender=None, task_id=None, retval=None, state=None, **kwargs):
    if state == "SUCCESS":
        notify_webhook(task_id, "SUCCESS", results=retval)
    elif state == "FAILURE":
        notify_webhook(task_id, "FAILURE", error=str(retval))

@task_failure.connect
def task_failed_handler(sender=None, task_id=None, exception=None, **kwargs):
    notify_webhook(task_id, "FAILURE", error=str(exception)) 