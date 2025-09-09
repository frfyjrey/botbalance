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


def _calculate_filled_quote_amount(exch_order: dict, max_quote_amount=None):
    """
    Calculate filled amount in quote currency (USDT) from exchange order data.

    Args:
        exch_order: Exchange order response
        max_quote_amount: Maximum quote amount to clamp result (order's quote_amount)

    Returns:
        Filled amount in quote currency (USDT) or None if cannot calculate
    """
    from decimal import Decimal

    # CORRECTED: Try cummulativeQuoteQty first (this is the actual filled amount)
    cum_quote = exch_order.get("cummulativeQuoteQty")
    if cum_quote is not None:
        try:
            filled_quote = Decimal(str(cum_quote))
            # Round to 8 decimal places to match Django model validation
            filled_quote = filled_quote.quantize(Decimal("0.00000001"))
            # Clamp to [0, max_quote_amount] if provided
            if max_quote_amount is not None:
                filled_quote = min(max(filled_quote, Decimal("0")), max_quote_amount)
            return filled_quote
        except (ValueError, TypeError):
            pass

    # Fallback: calculate from avgPrice * executedQty
    try:
        avg_price = exch_order.get("avgPrice") or exch_order.get("price", 0)
        executed_qty = exch_order.get("executedQty") or exch_order.get(
            "filled_amount", 0
        )

        if avg_price and executed_qty:
            filled_quote = Decimal(str(avg_price)) * Decimal(str(executed_qty))
            # Round to 8 decimal places to match Django model validation
            filled_quote = filled_quote.quantize(Decimal("0.00000001"))
            # Clamp to [0, max_quote_amount] if provided
            if max_quote_amount is not None:
                filled_quote = min(max(filled_quote, Decimal("0")), max_quote_amount)
            logger.debug(
                f"Calculated filled_quote: {avg_price} * {executed_qty} = {filled_quote}"
            )
            return filled_quote

    except (ValueError, TypeError, KeyError) as e:
        logger.warning(f"Cannot calculate filled quote amount from exchange data: {e}")

    return Decimal("0")  # Return 0 instead of None as safe fallback


@shared_task(bind=True, soft_time_limit=15, time_limit=20)
def poll_orders_task(self) -> dict[str, Any]:
    """
    Poll open orders for all users and synchronize statuses into DB.

    Safety guards:
    - Runs only when both EXCHANGE_ENV=live and ENABLE_ORDER_POLLING are True.
    - Uses get_open_orders per-user to minimize rate-limit, with fallback get_order_status.
    """
    from decimal import Decimal

    from django.conf import settings

    from botbalance.exchanges.models import ExchangeAccount
    from strategies.models import Order
    from strategies.views import prepare_exchange_data_for_json

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
                        # This happens when order is FILLED/CANCELLED and no longer in openOrders
                        try:
                            # Pass exactly one ID - prefer exchange order_id over client_order_id
                            if ex_id:
                                exch_order = asyncio.run(
                                    adapter.get_order_status(
                                        symbol=ord_obj.symbol,
                                        order_id=ex_id,
                                    )
                                )
                            elif cid:
                                exch_order = asyncio.run(
                                    adapter.get_order_status(
                                        symbol=ord_obj.symbol,
                                        client_order_id=cid,
                                    )
                                )
                            else:
                                logger.warning(
                                    f"No order_id or client_order_id for order {ord_obj.id}"
                                )
                                continue
                            logger.info(
                                f"Retrieved disappeared order status: {ord_obj.symbol} "
                                f"order_id={ex_id}, client_id={cid}, status={exch_order.get('status')}"
                            )
                        except Exception as e:
                            error_msg = str(e).lower()
                            # Handle specific exchange errors
                            if "-2011" in error_msg or "already closed" in error_msg:
                                # Order already cancelled on exchange
                                ord_obj.mark_cancelled()
                                logger.info(
                                    f"Order auto-cancelled (exchange): {ord_obj.symbol} order_id={ex_id}"
                                )
                                updated += 1
                                continue
                            elif "-2013" in error_msg or "does not exist" in error_msg:
                                # Order not found - possibly long-closed, will retry next tick
                                logger.warning(
                                    f"Order not found on exchange: {ord_obj.symbol} order_id={ex_id}, "
                                    f"client_id={cid} - will retry next tick"
                                )
                                continue
                            else:
                                logger.warning(
                                    f"Failed to get disappeared order status for {ord_obj.symbol} "
                                    f"order_id={ex_id}, client_id={cid}: {e}"
                                )
                                continue

                    # Map status to our model with consistency logic
                    binance_status = exch_order[
                        "status"
                    ].upper()  # Use original status from Binance
                    filled_quote = _calculate_filled_quote_amount(
                        exch_order, ord_obj.quote_amount
                    )

                    # Status consistency logic according to user's safe plan:
                    if binance_status in ["NEW", "OPEN"]:
                        # NEW = just created, should be 0
                        # OPEN = active on exchange, may be partially filled - use calculated value!
                        need_update = False
                        update_fields = []

                        if binance_status == "NEW" and ord_obj.filled_amount != Decimal(
                            "0"
                        ):
                            # Only reset to 0 for NEW orders (just created)
                            ord_obj.filled_amount = Decimal("0")
                            update_fields.extend(["filled_amount", "updated_at"])
                            need_update = True
                            logger.info(
                                f"Order NEW: {ord_obj.symbol} order_id={ex_id} - reset filled_amount to 0"
                            )
                        elif binance_status == "OPEN" and str(filled_quote) != str(
                            ord_obj.filled_amount
                        ):
                            # For OPEN orders, update with calculated filled_amount (may be partial)
                            # BUT: Don't decrease from existing partial fill to 0 (testnet bug protection)
                            old_filled = ord_obj.filled_amount

                            if filled_quote == Decimal(
                                "0"
                            ) and ord_obj.filled_amount > Decimal("0"):
                                # Testnet bug: /api/v3/order returns cummulativeQuoteQty=0 for OPEN orders
                                # Keep existing filled_amount to preserve partial fills
                                logger.info(
                                    f"Order OPEN: {ord_obj.symbol} order_id={ex_id} - preserving existing filled_amount {old_filled} (testnet protection)"
                                )
                            elif filled_quote > ord_obj.filled_amount:
                                # Only increase filled_amount (monotonic)
                                ord_obj.filled_amount = filled_quote
                                update_fields.extend(["filled_amount", "updated_at"])
                                need_update = True
                                fill_pct = (
                                    (
                                        float(filled_quote)
                                        / float(ord_obj.quote_amount)
                                        * 100
                                    )
                                    if ord_obj.quote_amount > 0
                                    else 0
                                )
                                logger.info(
                                    f"Order OPEN: {ord_obj.symbol} order_id={ex_id} - increased filled_amount: {old_filled} -> {filled_quote} ({fill_pct:.2f}%)"
                                )

                        # Update status to 'open' if currently 'submitted' and binance says OPEN
                        if binance_status == "OPEN" and ord_obj.status == "submitted":
                            ord_obj.status = "open"
                            update_fields.extend(["status", "updated_at"])
                            need_update = True
                            logger.info(
                                f"Order status updated: {ord_obj.symbol} order_id={ex_id} submitted -> open"
                            )

                        # Always save exchange_data for diagnostics
                        ord_obj.exchange_data = prepare_exchange_data_for_json(
                            exch_order
                        )
                        update_fields.append("exchange_data")
                        need_update = True

                        if need_update:
                            ord_obj.save(
                                update_fields=list(set(update_fields))
                            )  # Remove duplicates
                            updated += 1

                    elif binance_status == "PARTIALLY_FILLED":
                        # Update fill progress - filled_quote should be > 0 and < quote_amount
                        need_update = False
                        update_fields = ["exchange_data"]  # Always save exchange_data
                        ord_obj.exchange_data = prepare_exchange_data_for_json(
                            exch_order
                        )

                        if (
                            filled_quote > Decimal("0")
                            and filled_quote < ord_obj.quote_amount
                        ):
                            if str(filled_quote) != str(ord_obj.filled_amount):
                                old_filled = ord_obj.filled_amount
                                ord_obj.filled_amount = filled_quote
                                update_fields.extend(["filled_amount", "updated_at"])
                                need_update = True
                                logger.info(
                                    f"Order PARTIALLY_FILLED: {ord_obj.symbol} order_id={ex_id} "
                                    f"filled_quote: {old_filled} -> {filled_quote}"
                                )

                        if need_update or update_fields:
                            ord_obj.save(update_fields=list(set(update_fields)))
                            updated += 1
                        else:
                            # Safety guard: inconsistent data from testnet
                            logger.warning(
                                f"Order PARTIALLY_FILLED but invalid filled_quote={filled_quote} "
                                f"(should be >0 and <{ord_obj.quote_amount}): {ord_obj.symbol} order_id={ex_id}"
                            )

                    elif binance_status == "FILLED":
                        # Order completely filled - filled_amount = quote_amount (full execution)
                        # Save exchange_data first for diagnostics
                        ord_obj.exchange_data = prepare_exchange_data_for_json(
                            exch_order
                        )
                        ord_obj.mark_filled(filled_amount=ord_obj.quote_amount)
                        logger.info(
                            f"Order FILLED: {ord_obj.symbol} order_id={ex_id}, "
                            f"filled_amount={ord_obj.quote_amount}, prev_status={ord_obj.status}"
                        )
                        updated += 1

                    elif binance_status in ["CANCELED", "EXPIRED"]:
                        # IMPORTANT: Do NOT reset filled_amount - preserve partial fills
                        # Update filled_amount to correct value but keep partial executions
                        need_update = False
                        update_fields = ["exchange_data"]  # Always save exchange_data
                        ord_obj.exchange_data = prepare_exchange_data_for_json(
                            exch_order
                        )

                        if str(filled_quote) != str(ord_obj.filled_amount):
                            old_filled = ord_obj.filled_amount
                            ord_obj.filled_amount = filled_quote
                            update_fields.append("filled_amount")
                            need_update = True
                            logger.info(
                                f"Order CANCELLED with partial fill: {ord_obj.symbol} order_id={ex_id} "
                                f"filled_quote: {old_filled} -> {filled_quote}"
                            )

                        if ord_obj.status != "cancelled":
                            ord_obj.status = "cancelled"
                            update_fields.extend(["status", "updated_at"])
                            need_update = True
                            logger.info(
                                f"Order CANCELLED: {ord_obj.symbol} order_id={ex_id}, "
                                f"prev_status={ord_obj.status}"
                            )

                        if need_update or update_fields:
                            ord_obj.save(update_fields=list(set(update_fields)))
                            updated += 1

                    elif binance_status == "REJECTED":
                        error_msg = exch_order.get(
                            "error_message", "Unknown rejection reason"
                        )
                        # Save exchange_data first for diagnostics
                        ord_obj.exchange_data = prepare_exchange_data_for_json(
                            exch_order
                        )
                        ord_obj.mark_rejected(error_message=error_msg)
                        logger.info(
                            f"Order REJECTED: {ord_obj.symbol} order_id={ex_id}, "
                            f"prev_status={ord_obj.status}, reason={error_msg}"
                        )
                        updated += 1

                    else:
                        logger.warning(
                            f"Unknown order status: {ord_obj.symbol} order_id={ex_id}, "
                            f"binance_status={binance_status}, prev_status={ord_obj.status}"
                        )
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        f"Failed to sync order {ord_obj.symbol} order_id={ex_id} "
                        f"for user {acc.user_id}: {e}",
                        exc_info=True,
                    )
                    errors += 1

        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"poll_orders_task: account {acc.id} failed due to {e}", exc_info=True
            )
            errors += 1

    return {"status": "ok", "updated": updated, "errors": errors}


def _log_auto_trade_decision(
    user_id, connector_id, strategy_id, base, side, action, reason, coid=None
):
    """Log auto-trade decision with structured fields."""
    logger.info(
        f"AutoTrade decision: user={user_id}, connector={connector_id}, "
        f"strategy={strategy_id}, base={base}, side={side}, action={action}, "
        f"reason={reason}, coid={coid or 'N/A'}"
    )


@shared_task(bind=True, soft_time_limit=15, time_limit=20)
def strategy_tick_task(self) -> dict[str, Any]:
    """
    Automated strategy tick task for Step 6: Auto-Rebalance.

    Runs every 30 seconds to:
    1. Update portfolio states for connectors with active auto-trade strategies
    2. Calculate rebalance plans
    3. Execute cancel→place or place orders based on switch-cancel logic
    4. Respect limits: 1 operation per asset per tick, max 5 operations per tick
    """
    import asyncio
    import time

    from django.conf import settings
    from django.utils import timezone

    from botbalance.exchanges.models import ExchangeAccount
    from botbalance.exchanges.portfolio_service import portfolio_service
    from strategies.models import Order
    from strategies.rebalance_service import rebalance_service

    # Record tick start time for clock drift protection
    tick_start_time = time.time()

    # Check global auto-trade flag
    if not getattr(settings, "ENABLE_AUTO_TRADE", False):
        logger.info("strategy_tick_task skipped (ENABLE_AUTO_TRADE=False)")
        return {"status": "skipped", "reason": "auto_trade_disabled"}

    # Safety guard: do not run auto-trade in mock environment
    if getattr(settings, "EXCHANGE_ENV", "mock") == "mock":
        logger.info("strategy_tick_task skipped (EXCHANGE_ENV=mock)")
        return {"status": "skipped", "reason": "mock_environment"}

    processed_strategies = 0
    operations_performed = 0
    errors = 0
    max_operations_per_tick = 5

    # Get all active exchange accounts with their auto-trade strategies in one query
    from strategies.models import Strategy

    all_active_accounts = ExchangeAccount.objects.filter(
        is_active=True, account_type="spot"
    ).select_related("user")

    # Fetch all active auto-trade strategies for these accounts in one query
    strategies_by_account = {}
    active_strategies = Strategy.objects.filter(
        exchange_account__in=all_active_accounts,
        is_active=True,
        auto_trade_enabled=True,
    ).select_related("exchange_account")

    for strategy in active_strategies:
        strategies_by_account[strategy.exchange_account.id] = strategy

    accounts_with_auto_strategies = [
        account
        for account in all_active_accounts
        if account.id in strategies_by_account
    ]

    logger.info(
        f"Processing {len(accounts_with_auto_strategies)} accounts with auto-trade strategies"
    )

    for account in accounts_with_auto_strategies:
        if operations_performed >= max_operations_per_tick:
            logger.info(
                f"Reached max operations limit ({max_operations_per_tick}), stopping"
            )
            break

        try:
            # Get pre-loaded auto-trade strategy for this account
            strategy = strategies_by_account.get(account.id)  # type: ignore[assignment]
            if strategy is None:
                logger.warning(
                    f"No strategy found for account {account.id} - unexpected"
                )
                continue

            logger.info(
                f"Processing strategy {strategy.id} ({strategy.name}) for account {account.name}"
            )

            # Step 1: Update portfolio state with fresh prices for auto-trading
            state, error_code = asyncio.run(
                portfolio_service.upsert_portfolio_state(
                    account, source="tick", force_refresh_prices=True
                )
            )

            if error_code:
                logger.warning(
                    f"Skipping strategy {strategy.id}: portfolio state error {error_code}"
                )
                errors += 1
                continue

            # Check state freshness (must be within 60 seconds)
            if state:
                state_age_seconds = (timezone.now() - state.ts).total_seconds()
                state_age_ms = int(state_age_seconds * 1000)
                if state_age_seconds > 60:
                    logger.warning(
                        f"Skipping strategy {strategy.id}: portfolio state too old - "
                        f"age={state_age_ms}ms (>{60000}ms threshold), "
                        f"state_ts={state.ts.isoformat()}, reason=stale_portfolio_state"
                    )
                    errors += 1
                    continue
                else:
                    logger.debug(
                        f"Portfolio state age check passed: {state_age_ms}ms (strategy {strategy.id})"
                    )

            # Step 2: Calculate rebalance plan using fresh portfolio state
            plan = asyncio.run(
                rebalance_service.calculate_rebalance_plan(
                    strategy, account, portfolio_state=state, force_refresh_prices=True
                )
            )

            if not plan:
                logger.warning(
                    f"Skipping strategy {strategy.id}: failed to calculate plan"
                )
                errors += 1
                continue

            # Step 3: Get open orders from DB (not exchange)
            open_orders = Order.objects.filter(
                user=account.user,
                strategy=strategy,
                status__in=["pending", "submitted", "open"],
            )

            # Group orders by base asset and handle duplicates
            orders_by_base: dict[str, Order] = {}
            duplicate_orders_to_cancel = []

            for order in open_orders:
                if order.symbol.endswith(strategy.quote_asset):
                    base = order.symbol[: -len(strategy.quote_asset)]

                    if base in orders_by_base:
                        existing = orders_by_base[base]
                        if order.created_at > existing.created_at:
                            # New order is newer - cancel the existing one
                            duplicate_orders_to_cancel.append(existing)
                            orders_by_base[base] = order
                        else:
                            # Existing order is newer - cancel current one
                            duplicate_orders_to_cancel.append(order)
                    else:
                        orders_by_base[base] = order

            # Step 4: Plan уже содержит базовые активы, используем все actions
            filtered_actions = plan.actions

            # Cancel duplicate orders first
            adapter = account.get_adapter()
            cancelled_bases_this_tick = set()  # Track bases cancelled in this tick

            for dup_order in duplicate_orders_to_cancel:
                if operations_performed >= max_operations_per_tick:
                    logger.warning(
                        "Reached max operations limit, skipping duplicate cancellations"
                    )
                    break

                try:
                    base = dup_order.symbol[: -len(strategy.quote_asset)]
                    _log_auto_trade_decision(
                        account.user.id,
                        account.id,
                        strategy.id,
                        base,
                        dup_order.side,
                        "cancel",
                        "duplicate_order",
                        dup_order.client_order_id,
                    )

                    asyncio.run(
                        adapter.cancel_order(
                            account=account.account_type,
                            symbol=dup_order.symbol,
                            order_id=dup_order.exchange_order_id,
                        )
                    )
                    cancelled_bases_this_tick.add(
                        base
                    )  # Remember this base was cancelled
                    operations_performed += 1
                except Exception as e:
                    logger.error(
                        f"Failed to cancel duplicate order {dup_order.id}: {e}"
                    )
                    errors += 1

            # Step 5: Process each filtered asset
            for action in filtered_actions:
                if operations_performed >= max_operations_per_tick:
                    break

                base = action.asset  # "BTC", "ETH", etc
                if base == strategy.quote_asset:
                    continue  # пропускаем quote currency
                pair = f"{base}{strategy.quote_asset}"  # "BTCUSDT"
                existing_order = orders_by_base.get(base)

                try:
                    # Apply switch-cancel logic or place new order
                    operation_performed = asyncio.run(
                        _process_asset_tick(
                            strategy,
                            account,
                            action,
                            existing_order,
                            cancelled_bases_this_tick,
                            tick_start_time,
                        )
                    )

                    if operation_performed:
                        operations_performed += 1
                        logger.info(
                            f"Operation performed for base={base} pair={pair}: strategy={strategy.id}, "
                            f"action={action.action}"
                        )

                except Exception as e:
                    logger.error(
                        f"Error processing base={base} pair={pair}: {e}", exc_info=True
                    )
                    errors += 1

            # Step 6: Cancel orders for bases that are no longer in the universe
            plan_bases = set()
            for action in filtered_actions:
                plan_base = action.asset  # базовый актив напрямую
                if plan_base != strategy.quote_asset:
                    plan_bases.add(plan_base)

            orphaned_bases = set(orders_by_base.keys()) - plan_bases
            for orphaned_base in orphaned_bases:
                if operations_performed >= max_operations_per_tick:
                    logger.warning(
                        "Reached max operations limit, skipping orphaned base cancellations"
                    )
                    break

                orphaned_order = orders_by_base[orphaned_base]
                try:
                    _log_auto_trade_decision(
                        account.user.id,
                        account.id,
                        strategy.id,
                        orphaned_base,
                        orphaned_order.side,
                        "cancel",
                        "base_left_universe",
                        orphaned_order.client_order_id,
                    )

                    logger.info(
                        f"Cancelling orphaned order {orphaned_order.id} for base {orphaned_base} (left universe)"
                    )
                    asyncio.run(
                        adapter.cancel_order(
                            account=account.account_type,
                            symbol=orphaned_order.symbol,
                            order_id=orphaned_order.exchange_order_id,
                        )
                    )
                    cancelled_bases_this_tick.add(
                        orphaned_base
                    )  # Remember this base was cancelled
                    operations_performed += 1

                except Exception as e:
                    logger.error(
                        f"Failed to cancel orphaned order {orphaned_order.id}: {e}"
                    )
                    errors += 1

            processed_strategies += 1

        except Exception as e:
            logger.error(f"Error processing account {account.name}: {e}", exc_info=True)
            errors += 1

    return {
        "status": "completed",
        "processed_strategies": processed_strategies,
        "operations_performed": operations_performed,
        "errors": errors,
    }


async def _process_asset_tick(
    strategy,
    account,
    action,
    existing_order,
    cancelled_bases_this_tick,
    tick_start_time,
):
    """
    Process a single asset during strategy tick.
    Returns True if an operation (cancel/place) was performed.
    """

    base = action.asset  # базовый актив напрямую

    # Skip if this base was already cancelled this tick
    if base in cancelled_bases_this_tick:
        _log_auto_trade_decision(
            account.user.id,
            account.id,
            strategy.id,
            base,
            action.action,
            "skip",
            "cancelled_this_tick",
        )
        return False

    # Skip if action is 'hold' or has no meaningful trade
    if not hasattr(action, "action") or action.action == "hold":
        _log_auto_trade_decision(
            account.user.id,
            account.id,
            strategy.id,
            base,
            "hold",
            "skip",
            "hold_action",
        )
        return False

    if (
        not hasattr(action, "order_amount_normalized")
        or not action.order_amount_normalized
    ):
        _log_auto_trade_decision(
            account.user.id,
            account.id,
            strategy.id,
            base,
            action.action,
            "skip",
            "no_normalized_amount",
        )
        return False

    # Check minimum delta threshold
    if abs(action.delta_value) < (strategy.min_delta_pct / 100 * action.target_value):
        _log_auto_trade_decision(
            account.user.id,
            account.id,
            strategy.id,
            base,
            action.action,
            "skip",
            "below_min_delta",
        )
        return False

    adapter = account.get_adapter()

    # Case 1: Existing order exists
    if existing_order:
        # Check if we need to switch sides
        need_switch = _should_switch_order(existing_order, action, strategy)

        if need_switch:
            # Cancel existing order (place will happen in next tick after poller removes it)
            try:
                logger.info(
                    f"Cancelling existing order {existing_order.exchange_order_id} for side switch"
                )
                await adapter.cancel_order(
                    account=account.account_type,
                    symbol=existing_order.symbol,
                    order_id=existing_order.exchange_order_id,
                )

                # Do NOT modify status in DB - let poller handle it
                # Do NOT place new order in same tick - wait for next tick
                cancelled_bases_this_tick.add(base)  # Remember this base was cancelled
                _log_auto_trade_decision(
                    account.user.id,
                    account.id,
                    strategy.id,
                    base,
                    action.action,
                    "cancel",
                    "side_switch",
                    existing_order.client_order_id,
                )
                return True  # Cancel operation performed

            except Exception as e:
                # Check if error code indicates order already cancelled (-2011)
                error_msg = str(e).lower()
                if (
                    "-2011" in error_msg
                    or "already closed" in error_msg
                    or "already cancelled" in error_msg
                ):
                    logger.info(
                        f"Order {existing_order.exchange_order_id} already cancelled"
                    )
                    return True  # Consider this success
                else:
                    logger.error(f"Failed to cancel order {existing_order.id}: {e}")
                    return False
        else:
            # Same side - determine if it's partial fill or just same side
            is_partial_fill = (
                existing_order.filled_amount > 0 and existing_order.status == "open"
            )

            if is_partial_fill:
                reason = "partial_fill"
                logger.info(
                    f"Keeping partially filled order {existing_order.id}: "
                    f"filled_amount={existing_order.filled_amount}, "
                    f"total_amount={existing_order.quote_amount}"
                )
            else:
                reason = "same_side"

            _log_auto_trade_decision(
                account.user.id,
                account.id,
                strategy.id,
                base,
                action.action,
                "skip",
                reason,
            )
            return False
    else:
        # Case 2: No existing order - place new if needed
        return await _place_new_order(
            strategy, account, action, adapter, tick_start_time
        )

    return False


def _should_switch_order(existing_order, action, strategy):
    """
    Determine if we should cancel existing order and place new one.
    Only switch on side change + sufficient price drift.
    """

    # Must be different sides (convert action to side)
    action_side = action.action  # buy/sell
    if existing_order.side == action_side:
        return False

    # Calculate price drift percentage
    if (
        not hasattr(action, "normalized_order_price")
        or not action.normalized_order_price
    ):
        return False

    existing_price = existing_order.limit_price
    plan_price = action.normalized_order_price

    # Safe drift calculation with proper validation
    if existing_price <= 0 or plan_price <= 0:
        return False

    drift_pct = abs(plan_price - existing_price) / existing_price * 100
    threshold_pct = strategy.switch_cancel_buffer_pct
    will_switch = drift_pct >= threshold_pct

    # Log drift calculation details for debugging
    logger.debug(
        f"Switch-cancel drift calculation: existing_price={existing_price}, "
        f"new_price={plan_price}, drift_pct={drift_pct:.3f}%, "
        f"threshold_pct={threshold_pct}%, will_switch={will_switch}"
    )

    return will_switch


async def _place_new_order(strategy, account, action, adapter, tick_start_time):
    """
    Place new order based on rebalance action.
    Returns True if order was successfully placed.
    """
    import hashlib
    import time
    from decimal import Decimal

    from asgiref.sync import sync_to_async
    from django.utils import timezone

    from strategies.models import Order
    from strategies.views import prepare_exchange_data_for_json

    # Async обертки для Django ORM
    @sync_to_async
    def get_existing_live_orders(user, strategy, quote_asset):
        return list(
            Order.objects.filter(
                user=user,
                strategy=strategy,
                status__in=["pending", "submitted", "open"],
                symbol__endswith=quote_asset,
            )
        )

    @sync_to_async
    def check_order_exists(client_order_id):
        return Order.objects.filter(client_order_id=client_order_id).exists()

    @sync_to_async
    def create_order(**kwargs):
        return Order.objects.create(**kwargs)

    try:
        # Определяем базовый актив и торговую пару
        base = action.asset  # базовый актив напрямую
        pair = f"{base}{strategy.quote_asset}"  # торговая пара для биржи

        # Clock drift protection: if tick is running too long, skip place operations
        elapsed_seconds = time.time() - tick_start_time
        if elapsed_seconds > 60:
            logger.warning(
                f"Skipping place for {base}: tick running too long ({elapsed_seconds:.1f}s > 60s threshold) - "
                f"possible clock drift or worker lag"
            )
            _log_auto_trade_decision(
                account.user.id,
                account.id,
                strategy.id,
                base,
                action.action,
                "skip",
                "clock_drift_protection",
            )
            return False

        # Critical safety check: ensure no live orders exist for this base
        # This protects against race conditions between ticks
        base = action.asset  # базовый актив напрямую
        pair = f"{base}{strategy.quote_asset}"

        existing_live_orders = await get_existing_live_orders(
            account.user, strategy, strategy.quote_asset
        )

        # Check if any live order matches this base
        for order in existing_live_orders:
            order_base = order.symbol[: -len(strategy.quote_asset)]
            if order_base == base:
                _log_auto_trade_decision(
                    account.user.id,
                    account.id,
                    strategy.id,
                    base,
                    action.action,
                    "skip",
                    "live_order_still_exists",
                    order.client_order_id,
                )
                logger.warning(
                    f"Skipping place for {base} - live order {order.id} still exists in DB"
                )
                return False

        side = action.action  # buy/sell
        limit_price = action.normalized_order_price
        quote_amount = action.order_amount_normalized

        # Generate idempotent client_order_id for auto-trade
        ts_tick = (int(time.time()) // 30) * 30  # 30-second tick window

        # Use normalized strings without exponential notation (critical for idempotency)
        def normalize_decimal_string(value):
            """Convert Decimal to string without exponential notation."""
            if value is None:
                return "0"
            # Format as fixed-point notation, strip trailing zeros
            return format(value, "f").rstrip("0").rstrip(".")

        normalized_price = normalize_decimal_string(limit_price)
        normalized_quote = normalize_decimal_string(quote_amount)

        coid_seed = f"auto:{strategy.id}:{account.id}:{base}:{side}:{normalized_price}:{normalized_quote}:{ts_tick}"
        client_order_id = hashlib.sha1(coid_seed.encode()).hexdigest()[:20]

        # Check if order with this client_order_id already exists
        if await check_order_exists(client_order_id):
            logger.info(
                f"Order with client_order_id {client_order_id} already exists, skipping"
            )
            return False

        logger.info(
            f"Placing auto-trade order: {side} {pair} @ {limit_price}, amount: {quote_amount}"
        )

        # Place order through exchange adapter
        exchange_order = await adapter.place_order(
            account=account.account_type,
            symbol=pair,
            side=side,
            limit_price=limit_price,
            quote_amount=quote_amount,
            client_order_id=client_order_id,
        )

        # Create Order record in database
        await create_order(
            user=account.user,
            strategy=strategy,
            execution=None,  # Auto-trade orders don't belong to manual executions
            exchange_order_id=exchange_order["id"],
            client_order_id=client_order_id,
            exchange=account.exchange,
            symbol=pair,
            side=side,
            status="submitted",
            limit_price=exchange_order["limit_price"],
            quote_amount=exchange_order["quote_amount"],
            filled_amount=Decimal("0"),  # Always 0 at creation - poller will update
            submitted_at=timezone.now(),
            exchange_data=prepare_exchange_data_for_json(
                dict(exchange_order)
            ),  # Save exchange data for diagnostics
        )

        _log_auto_trade_decision(
            account.user.id,
            account.id,
            strategy.id,
            base,
            side,
            "place",
            "new_order",
            client_order_id,
        )

        return True

    except Exception as e:
        logger.error(f"Failed to place auto-trade order for {pair}: {e}", exc_info=True)
        return False
