"""
Celery tasks for the botbalance project.

This module contains background tasks that can be executed asynchronously.
"""

import logging
import time
from typing import Any

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def echo_task(self, message: str, delay: int = 0) -> dict[str, Any]:
    """
    Echo task that returns the input message after optional delay.

    This is a simple example task for testing Celery functionality.

    Args:
        message (str): Message to echo back
        delay (int): Seconds to wait before returning (default: 0)

    Returns:
        Dict containing the original message, task info, and timing
    """
    logger.info(f"Echo task started with message: '{message}', delay: {delay}s")

    start_time = time.time()

    # Simulate work with delay
    if delay > 0:
        logger.info(f"Sleeping for {delay} seconds...")
        time.sleep(delay)

    end_time = time.time()
    execution_time = end_time - start_time

    result = {
        "message": message,
        "task_id": self.request.id,
        "delay_requested": delay,
        "execution_time": round(execution_time, 2),
        "status": "completed",
        "timestamp": int(end_time),
    }

    logger.info(f"Echo task completed in {execution_time:.2f}s")
    return result


@shared_task
def heartbeat_task() -> dict[str, Any]:
    """
    Heartbeat task for system health monitoring.

    This task can be used to verify that Celery workers are running
    and processing tasks correctly.

    Returns:
        Dict containing system status and timestamp
    """
    logger.info("Heartbeat task executed")

    import django
    from django.conf import settings

    result = {
        "status": "alive",
        "message": "Celery worker is running",
        "timestamp": int(time.time()),
        "django_version": django.get_version(),
        "debug_mode": settings.DEBUG,
        "system": "botbalance-backend",
    }

    return result


@shared_task(bind=True)
def long_running_task(self, duration: int = 10) -> dict[str, Any]:
    """
    Long running task for testing task tracking and cancellation.

    This task updates its progress and can be monitored via the task status API.

    Args:
        duration (int): How long the task should run (in seconds)

    Returns:
        Dict containing task completion info
    """
    logger.info(f"Starting long running task for {duration} seconds")

    for i in range(duration):
        # Update task state with progress
        self.update_state(
            state="PROGRESS",
            meta={
                "current": i + 1,
                "total": duration,
                "status": f"Processing step {i + 1}/{duration}",
            },
        )
        time.sleep(1)

    result = {
        "status": "completed",
        "duration": duration,
        "message": f"Long running task completed after {duration} seconds",
        "timestamp": int(time.time()),
    }

    logger.info(f"Long running task completed after {duration} seconds")
    return result
