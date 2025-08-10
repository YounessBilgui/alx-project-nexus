import os
from celery import Celery
from decouple import config

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pollsystem.settings")

app = Celery("pollsystem")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Configuration Options
app.conf.update(
    broker_url=config("CELERY_BROKER_URL", default="redis://localhost:6379/0"),
    result_backend=config("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0"),
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
