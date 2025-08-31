"""
Celery configuration for botbalance project.
"""

import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "botbalance.settings.local")

app = Celery("botbalance")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f"Request: {self.request!r}")


@app.task
def heartbeat():
    """Simple heartbeat task for health checks."""
    import logging

    logger = logging.getLogger(__name__)
    logger.info("Celery heartbeat - system is alive")
    return {"status": "alive", "message": "Celery worker is running"}
