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


@shared_task(bind=True, soft_time_limit=15, time_limit=20)
def poll_orders_task(self) -> dict[str, Any]:
    """
    Poll open orders for all users and synchronize statuses into DB.

    Safety guards:
    - Runs only when both EXCHANGE_ENV=live and ENABLE_ORDER_POLLING are True.
    - Uses get_open_orders per-user to minimize rate-limit, with fallback get_order_status.
    """
    from django.conf import settings

    from botbalance.exchanges.models import ExchangeAccount
    from strategies.models import Order

    if getattr(settings, "EXCHANGE_ENV", "mock") == "mock" or not getattr(
        settings, "ENABLE_ORDER_POLLING", False
    ):
        logger.info("poll_orders_task skipped (feature flags disabled)")
        return {"status": "skipped", "reason": "feature_flags_disabled"}

    updated = 0
    errors = 0

    # Active users having active exchange accounts
    accounts = (
        ExchangeAccount.objects.filter(is_active=True, account_type="spot")
        .select_related("user")
        .all()
    )

    for acc in accounts:
        try:
            adapter = acc.get_adapter()
            # 1) Fetch all open orders from exchange (single call per account)
            import asyncio

            open_orders = asyncio.run(adapter.get_open_orders(account=acc.account_type))

            # Build quick lookup: (exchange_id, client_id) -> exchange order data
            by_id = {str(o["id"]): o for o in open_orders}
            by_cid = {
                str(o["client_order_id"]): o
                for o in open_orders
                if o.get("client_order_id")
            }

            # 2) Load our active orders for this user
            active_qs = Order.objects.filter(
                user=acc.user,
                status__in=["pending", "submitted", "open"],
            )

            for ord_obj in active_qs:
                try:
                    ex_id = str(ord_obj.exchange_order_id or "")
                    cid = str(ord_obj.client_order_id or "")
                    exch_order = by_id.get(ex_id) or (by_cid.get(cid) if cid else None)

                    if not exch_order:
                        # Fallback: query direct status if absent from openOrders
                        try:
                            exch_order = asyncio.run(
                                adapter.get_order_status(ex_id or cid)
                            )
                        except Exception:
                            # If still not found — assume it might be filled/cancelled
                            # Next iteration will reconcile; skip for now
                            continue

                    # Map status to our model
                    status = exch_order["status"].lower()
                    if status == "open":
                        # Update fill progress only
                        new_filled = exch_order.get("filled_amount")
                        if new_filled is not None and str(new_filled) != str(
                            ord_obj.filled_amount
                        ):
                            ord_obj.filled_amount = new_filled
                            ord_obj.save(update_fields=["filled_amount", "updated_at"])
                            updated += 1
                    elif status == "filled":
                        ord_obj.mark_filled(
                            filled_amount=exch_order.get("filled_amount")
                        )
                        updated += 1
                    elif status == "cancelled":
                        ord_obj.mark_cancelled()
                        updated += 1
                    elif status == "rejected":
                        ord_msg = ""
                        ord_obj.mark_rejected(error_message=ord_msg)
                        updated += 1
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        f"Failed to sync order {ord_obj.id} for user {acc.user_id}: {e}"
                    )
                    errors += 1

        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"poll_orders_task: account {acc.id} failed due to {e}", exc_info=True
            )
            errors += 1

    return {"status": "ok", "updated": updated, "errors": errors}
