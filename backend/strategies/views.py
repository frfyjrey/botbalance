"""
API views for trading strategies (Step 3: Target Allocation & Step 4: Manual Rebalance).
"""

import asyncio
import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from botbalance.exchanges.models import ExchangeAccount

from .constants import ALL_ALLOCATION_ASSETS, QUOTE_ASSET_SYMBOLS
from .models import Order, RebalanceExecution, Strategy
from .rebalance_service import (
    NoActiveStrategyError,
    NoPricingDataError,
    RateLimitExceededError,
    RebalanceError,
    rebalance_service,
)
from .serializers import (
    RebalancePlanSerializer,
    StrategyCreateRequestSerializer,
    StrategySerializer,
    StrategyUpdateRequestSerializer,
)

logger = logging.getLogger(__name__)


def prepare_exchange_data_for_json(exchange_order_dict: dict) -> dict:
    """
    Convert Decimal objects to strings for JSON serialization.

    Django JSONField cannot serialize Decimal objects directly,
    so we need to convert them to strings before storage.

    Args:
        exchange_order_dict: Dictionary containing exchange order data

    Returns:
        dict: Dictionary with Decimal values converted to strings
    """
    result = {}
    for key, value in exchange_order_dict.items():
        if isinstance(value, Decimal):
            result[key] = str(value)
        else:
            result[key] = value
    return result


@api_view(["GET", "POST", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def user_strategy_view(request):
    """Manage user's trading strategy."""
    try:
        if request.method == "GET":
            return _get_user_strategy(request)
        elif request.method == "POST":
            return _create_or_update_strategy(request)
        elif request.method == "PATCH":
            return _patch_strategy(request)
        elif request.method == "DELETE":
            return _delete_strategy(request)
    except Exception as e:
        logger.error(f"Error in user_strategy_view: {e}", exc_info=True)
        return Response(
            {
                "status": "error",
                "message": "Internal server error occurred",
                "error_code": "STRATEGY_ERROR",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Explicitly handle unexpected HTTP methods
    return Response(
        {
            "status": "error",
            "message": f"Method {request.method} not allowed.",
            "error_code": "METHOD_NOT_ALLOWED",
        },
        status=status.HTTP_405_METHOD_NOT_ALLOWED,
    )


def _get_user_strategy(request):
    """Get user's current strategy."""
    strategy = Strategy.objects.filter(user=request.user).first()

    if not strategy:
        return Response(
            {
                "status": "success",
                "message": "No strategy found",
                "strategy": None,
            }
        )

    serializer = StrategySerializer(strategy, context={"request": request})
    return Response(
        {
            "status": "success",
            "strategy": serializer.data,
        }
    )


def _create_or_update_strategy(request):
    """Create new strategy or update existing one."""
    existing_strategy = Strategy.objects.filter(user=request.user).first()

    if existing_strategy:
        # Update existing strategy
        serializer = StrategyUpdateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "status": "error",
                    "message": "Invalid strategy data",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        strategy_serializer = StrategySerializer(
            existing_strategy,
            data=serializer.validated_data,
            partial=True,
            context={"request": request},
        )

        if strategy_serializer.is_valid():
            try:
                strategy = strategy_serializer.save()
                # Validate model constraints (including base currency in allocations)
                strategy.full_clean()
                return Response(
                    {
                        "status": "success",
                        "message": "Strategy updated successfully",
                        "strategy": StrategySerializer(
                            strategy, context={"request": request}
                        ).data,
                    }
                )
            except ValidationError as e:
                error_message = "Validation failed"
                errors = {}

                if hasattr(e, "message_dict"):
                    errors = e.message_dict
                elif hasattr(e, "messages"):
                    error_message = "; ".join(e.messages)
                else:
                    error_message = str(e)

                return Response(
                    {
                        "status": "error",
                        "message": error_message,
                        "errors": errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {
                    "status": "error",
                    "message": "Failed to update strategy",
                    "errors": strategy_serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    else:
        # Create new strategy
        serializer = StrategyCreateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "status": "error",
                    "message": "Invalid strategy data",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        strategy_serializer = StrategySerializer(
            data=serializer.validated_data, context={"request": request}
        )

        if strategy_serializer.is_valid():
            try:
                strategy = strategy_serializer.save()
                # Validate model constraints (including base currency in allocations)
                strategy.full_clean()
                return Response(
                    {
                        "status": "success",
                        "message": "Strategy created successfully",
                        "strategy": StrategySerializer(
                            strategy, context={"request": request}
                        ).data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            except ValidationError as e:
                # Delete the strategy if validation fails
                if strategy and strategy.pk:
                    strategy.delete()

                error_message = "Validation failed"
                errors = {}

                if hasattr(e, "message_dict"):
                    errors = e.message_dict
                elif hasattr(e, "messages"):
                    error_message = "; ".join(e.messages)
                else:
                    error_message = str(e)

                return Response(
                    {
                        "status": "error",
                        "message": error_message,
                        "errors": errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {
                    "status": "error",
                    "message": "Failed to create strategy",
                    "errors": strategy_serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


def _patch_strategy(request):
    """Partially update user's existing strategy (e.g., toggle is_active)."""
    # Get user's existing strategy
    try:
        strategy = Strategy.objects.get(user=request.user)
    except Strategy.DoesNotExist:
        return Response(
            {
                "status": "error",
                "message": "No strategy found. Create a strategy first.",
                "error_code": "STRATEGY_NOT_FOUND",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # Update strategy with partial data
    serializer = StrategyUpdateRequestSerializer(data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(
            {
                "status": "error",
                "message": "Invalid strategy data",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Use StrategySerializer to update the strategy
    strategy_serializer = StrategySerializer(
        strategy,
        data=serializer.validated_data,
        partial=True,
        context={"request": request},
    )

    if strategy_serializer.is_valid():
        try:
            strategy = strategy_serializer.save()
            # Validate model constraints (including base currency in allocations)
            strategy.full_clean()
            return Response(
                {
                    "status": "success",
                    "message": "Strategy updated successfully",
                    "strategy": StrategySerializer(
                        strategy, context={"request": request}
                    ).data,
                },
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            error_message = "Validation failed"
            errors = {}

            if hasattr(e, "message_dict"):
                errors = e.message_dict
            elif hasattr(e, "messages"):
                error_message = "; ".join(e.messages)
            else:
                error_message = str(e)

            return Response(
                {
                    "status": "error",
                    "message": error_message,
                    "errors": errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
    else:
        return Response(
            {
                "status": "error",
                "message": "Failed to update strategy",
                "errors": strategy_serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


def _delete_strategy(request):
    """Delete user's strategy and all related data."""
    try:
        strategy = Strategy.objects.get(user=request.user)
    except Strategy.DoesNotExist:
        return Response(
            {
                "status": "error",
                "message": "No strategy found.",
                "error_code": "STRATEGY_NOT_FOUND",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    strategy_name = strategy.name
    strategy.delete()

    return Response(
        {
            "status": "success",
            "message": f"Strategy '{strategy_name}' deleted successfully",
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def rebalance_plan_view(request):
    """Calculate rebalancing plan for user's strategy."""
    try:
        sanitized_user = str(request.user).replace("\r", "").replace("\n", "")
        logger.info(f"Rebalance plan request from user: {sanitized_user}")

        # Get user's strategy
        strategy = Strategy.objects.filter(user=request.user).first()
        logger.info(f"Found strategy: {strategy}")

        if not strategy:
            sanitized_user = str(request.user).replace("\r", "").replace("\n", "")
            logger.warning(f"No strategy found for user {sanitized_user}")
            return Response(
                {
                    "status": "error",
                    "message": "No trading strategy found. Please create a strategy first.",
                    "error_code": "NO_STRATEGY",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if strategy has valid allocations
        if not strategy.is_allocation_valid():
            return Response(
                {
                    "status": "error",
                    "message": f"Strategy allocations are invalid. Total: {strategy.get_total_allocation()}%",
                    "error_code": "INVALID_STRATEGY",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get user's exchange account
        exchange_account = ExchangeAccount.objects.filter(
            user=request.user, is_active=True
        ).first()

        if not exchange_account:
            return Response(
                {
                    "status": "error",
                    "message": "No active exchange account found. Please add an exchange account first.",
                    "error_code": "NO_EXCHANGE_ACCOUNT",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Calculate rebalance plan
        force_refresh = (
            request.query_params.get("force_refresh", "false").lower() == "true"
        )

        try:
            logger.info(
                f"Calling calculate_rebalance_plan for strategy: {strategy.name}"
            )
            plan = asyncio.run(
                rebalance_service.calculate_rebalance_plan(
                    strategy, exchange_account, force_refresh
                )
            )
            logger.info("Successfully calculated rebalance plan")
        except NoPricingDataError as e:
            logger.warning(f"Caught NoPricingDataError: {e}")
            return Response(
                {
                    "status": "error",
                    "message": str(e),
                    "error_code": e.error_code,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except NoActiveStrategyError as e:
            logger.warning(f"Caught NoActiveStrategyError: {e} - returning HTTP 409")
            return Response(
                {
                    "status": "error",
                    "message": str(e),
                    "error_code": e.error_code,
                },
                status=status.HTTP_409_CONFLICT,
            )
        except RateLimitExceededError as e:
            return Response(
                {
                    "status": "error",
                    "message": str(e),
                    "error_code": e.error_code,
                    "retry_after_seconds": 5,  # Suggest retry after cooldown
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except RebalanceError as e:
            return Response(
                {
                    "status": "error",
                    "message": str(e),
                    "error_code": e.error_code,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not plan:
            return Response(
                {
                    "status": "error",
                    "message": "Failed to calculate rebalance plan. Please try again later.",
                    "error_code": "PLAN_CALCULATION_FAILED",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Convert plan to dict for serialization (include normalized params for visibility)
        plan_data = {
            "strategy_id": plan.strategy_id,
            "strategy_name": plan.strategy_name,
            "portfolio_nav": plan.portfolio_nav,
            "quote_currency": plan.quote_currency,
            "actions": [
                {
                    "asset": action.asset,
                    "action": action.action,
                    "current_percentage": action.current_percentage,
                    "target_percentage": action.target_percentage,
                    "current_value": action.current_value,
                    "target_value": action.target_value,
                    "delta_value": action.delta_value,
                    "order_amount": action.order_amount,
                    "order_volume": action.order_volume,
                    "order_price": action.order_price,
                    "market_price": action.market_price,
                    "normalized_order_volume": action.normalized_order_volume,
                    "normalized_order_price": action.normalized_order_price,
                    "order_amount_normalized": action.order_amount_normalized,
                }
                for action in plan.actions
            ],
            "total_delta": plan.total_delta,
            "orders_needed": plan.orders_needed,
            "rebalance_needed": plan.rebalance_needed,
            "calculated_at": plan.calculated_at,
            "exchange_account": plan.exchange_account,
        }

        serializer = RebalancePlanSerializer(data=plan_data)
        if not serializer.is_valid():
            logger.error(f"Plan serialization failed: {serializer.errors}")
            return Response(
                {
                    "status": "error",
                    "message": "Failed to serialize rebalance plan",
                    "error_code": "SERIALIZATION_ERROR",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "status": "success",
                "plan": serializer.data,
            }
        )

    except Exception as e:
        logger.error(f"Error calculating rebalance plan: {e}", exc_info=True)
        return Response(
            {
                "status": "error",
                "message": "Failed to calculate rebalance plan due to internal error",
                "error_code": "REBALANCE_PLAN_ERROR",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def strategy_activate_view(request):
    """Activate or deactivate user's strategy."""
    try:
        strategy = get_object_or_404(Strategy, user=request.user)

        is_active = request.data.get("is_active")
        if is_active is None:
            return Response(
                {
                    "status": "error",
                    "message": "Missing 'is_active' field",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(is_active, bool):
            return Response(
                {
                    "status": "error",
                    "message": "'is_active' must be a boolean",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate strategy before activation
        if is_active and not strategy.is_allocation_valid():
            return Response(
                {
                    "status": "error",
                    "message": f"Cannot activate strategy with invalid allocations. Total: {strategy.get_total_allocation()}%",
                    "error_code": "INVALID_STRATEGY",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        strategy.is_active = is_active
        strategy.save(update_fields=["is_active", "updated_at"])

        action = "activated" if is_active else "deactivated"

        return Response(
            {
                "status": "success",
                "message": f"Strategy {action} successfully",
                "strategy": StrategySerializer(
                    strategy, context={"request": request}
                ).data,
            }
        )

    except Strategy.DoesNotExist:
        return Response(
            {
                "status": "error",
                "message": "No strategy found",
                "error_code": "NO_STRATEGY",
            },
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        logger.error(f"Error activating/deactivating strategy: {e}", exc_info=True)
        return Response(
            {
                "status": "error",
                "message": "Failed to update strategy status",
                "error_code": "STRATEGY_UPDATE_ERROR",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def rebalance_execute_view(request):
    """
    Execute rebalancing by placing orders according to strategy plan.

    Step 4: Manual rebalance execution.
    Creates orders through exchange adapter and stores them in the database.
    """
    try:
        sanitized_user = str(request.user).replace("\r", "").replace("\n", "")
        logger.info(f"Rebalance execute request from user: {sanitized_user}")

        # Get user's strategy
        strategy = Strategy.objects.filter(user=request.user).first()

        if not strategy:
            return Response(
                {
                    "status": "error",
                    "message": "No trading strategy found. Please create a strategy first.",
                    "error_code": "NO_STRATEGY",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if strategy has valid allocations
        if not strategy.is_allocation_valid():
            return Response(
                {
                    "status": "error",
                    "message": f"Strategy allocations are invalid. Total: {strategy.get_total_allocation()}%",
                    "error_code": "INVALID_STRATEGY",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get user's exchange account
        exchange_account = ExchangeAccount.objects.filter(
            user=request.user, is_active=True
        ).first()

        if not exchange_account:
            return Response(
                {
                    "status": "error",
                    "message": "No active exchange account found. Please add an exchange account first.",
                    "error_code": "NO_EXCHANGE_ACCOUNT",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get rebalance plan
        force_refresh_prices = request.data.get("force_refresh_prices", False)
        try:
            rebalance_plan = asyncio.run(
                rebalance_service.calculate_rebalance_plan(
                    strategy, exchange_account, force_refresh_prices
                )
            )
        except NoPricingDataError as e:
            return Response(
                {
                    "status": "error",
                    "message": str(e),
                    "error_code": e.error_code,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except NoActiveStrategyError as e:
            logger.warning(
                f"Caught NoActiveStrategyError in execute: {e} - returning HTTP 409"
            )
            return Response(
                {
                    "status": "error",
                    "message": str(e),
                    "error_code": e.error_code,
                },
                status=status.HTTP_409_CONFLICT,
            )
        except RateLimitExceededError as e:
            return Response(
                {
                    "status": "error",
                    "message": str(e),
                    "error_code": e.error_code,
                    "retry_after_seconds": 5,  # Suggest retry after cooldown
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except RebalanceError as e:
            return Response(
                {
                    "status": "error",
                    "message": str(e),
                    "error_code": e.error_code,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not rebalance_plan or not rebalance_plan.actions:
            return Response(
                {
                    "status": "success",
                    "message": "Portfolio is already balanced. No orders needed.",
                    "orders_created": 0,
                    "total_delta": "0.00",
                    "nav": str(
                        rebalance_plan.portfolio_nav if rebalance_plan else "0.00"
                    ),
                }
            )

        # At this point rebalance_plan is guaranteed to be not None
        assert rebalance_plan is not None

        # Create rebalance execution record
        execution = RebalanceExecution.objects.create(
            strategy=strategy,
            status="in_progress",
            portfolio_nav=rebalance_plan.portfolio_nav,
            total_delta=sum(
                abs(action.delta_value) for action in rebalance_plan.actions
            ),
            orders_count=len(rebalance_plan.actions),
        )

        logger.info(
            f"Created rebalance execution {execution.id} for strategy {strategy.id}"
        )

        # Create orders through exchange adapter
        created_orders = []
        exchange_adapter = exchange_account.get_adapter()

        try:
            import hashlib
            from math import floor

            from django.utils import timezone

            # Use 30-second tick for idempotent client ids
            ts_tick = int(floor(timezone.now().timestamp() / 30)) * 30

            for index, action in enumerate(rebalance_plan.actions):
                # Skip orders for quote currency pairs like USDTUSDT
                if action.asset == str(rebalance_plan.quote_currency):
                    logger.info(
                        f"Skipping order for quote asset {action.asset} (no self-quote trades)"
                    )
                    continue
                # Calculate minimum delta threshold for this action based on percentage
                min_delta_threshold = action.target_value * strategy.min_delta_pct / 100
                if abs(action.delta_value) < min_delta_threshold:
                    logger.info(
                        f"Skipping {action.asset} delta {action.delta_value} below minimum threshold {min_delta_threshold} ({strategy.min_delta_pct}%)"
                    )
                    continue

                # Determine order parameters
                symbol = action.asset + "USDT"  # Assuming USDT pairs for now
                side = "buy" if action.delta_value > 0 else "sell"
                # Use order_amount from Engine (capped by order_size_pct)
                quote_amount = (
                    abs(action.order_amount)
                    if action.order_amount is not None
                    else abs(action.delta_value)
                )

                # Use precomputed order_price from plan (Engine logic: buy below, sell above)
                limit_price = action.order_price
                if not limit_price:
                    # Fallback: compute from market price and step pct (buy below, sell above)
                    market_price = action.market_price
                    if not market_price:
                        logger.warning(f"No market price for {symbol}, skipping order")
                        continue
                    step = strategy.order_step_pct / Decimal("100")
                    limit_price = (
                        market_price * (Decimal("1") - step)
                        if side == "buy"
                        else market_price * (Decimal("1") + step)
                    )

                # Generate client order ID for idempotency
                coid_seed = f"{request.user.id}:{symbol}:{side}:{ts_tick}:{index}"
                client_order_id = hashlib.sha1(coid_seed.encode()).hexdigest()[:20]

                # Place order through exchange adapter
                logger.info(
                    f"Placing {side} order for {symbol}: {quote_amount} at {limit_price}"
                )

                exchange_order = asyncio.run(
                    exchange_adapter.place_order(
                        account="spot",
                        symbol=symbol,
                        side=side,
                        limit_price=limit_price,
                        quote_amount=quote_amount,
                        client_order_id=client_order_id,
                    )
                )

                # Create Order record in database
                order = Order.objects.create(
                    user=request.user,
                    strategy=strategy,
                    execution=execution,
                    exchange_order_id=exchange_order["id"],
                    client_order_id=client_order_id,
                    exchange=exchange_account.exchange,
                    symbol=symbol,
                    side=side,
                    status="submitted",  # Mark as submitted since exchange accepted it
                    limit_price=exchange_order["limit_price"],
                    quote_amount=exchange_order["quote_amount"],
                    filled_amount=exchange_order["filled_amount"],
                    submitted_at=timezone.now(),
                    exchange_data=prepare_exchange_data_for_json(
                        dict(exchange_order)
                    ),  # Convert Decimal to strings for JSON storage
                )

                created_orders.append(order)
                logger.info(
                    f"Created Order {order.id} with exchange ID {exchange_order['id']}"
                )

            # Mark execution as completed
            execution.orders_count = len(created_orders)
            execution.mark_completed()

            # Update strategy last rebalanced timestamp
            strategy.last_rebalanced_at = timezone.now()
            strategy.save(update_fields=["last_rebalanced_at"])

            logger.info(
                f"Rebalance execution {execution.id} completed with {len(created_orders)} orders"
            )

            # Prepare response
            orders_data = []
            for order in created_orders:
                orders_data.append(
                    {
                        "id": order.id,
                        "exchange_order_id": order.exchange_order_id,
                        "symbol": order.symbol,
                        "side": order.side,
                        "status": order.status,
                        "limit_price": str(order.limit_price),
                        "quote_amount": str(order.quote_amount),
                        "created_at": order.created_at.isoformat(),
                    }
                )

            # NEW: Update PortfolioState then create snapshot after order execution (Stage B integration)
            try:
                from botbalance.exchanges.portfolio_service import portfolio_service
                from botbalance.exchanges.snapshot_service import snapshot_service

                # 1. Update PortfolioState with order_fill source
                logger.info(
                    f"Updating PortfolioState after order execution for {exchange_account.name}"
                )
                portfolio_state, error_code = asyncio.run(
                    portfolio_service.upsert_portfolio_state(
                        exchange_account,
                        source="order_fill",
                    )
                )

                if error_code == "ERROR_PRICING":
                    logger.warning(
                        f"Cannot create snapshot for user {sanitized_user}: pricing data unavailable after order execution"
                    )
                elif error_code:
                    logger.warning(
                        f"Cannot create snapshot for user {sanitized_user}: PortfolioState error: {error_code}"
                    )
                elif portfolio_state:
                    # 2. Create snapshot from updated State
                    snapshot = asyncio.run(
                        snapshot_service.create_snapshot_from_state(
                            user=request.user,
                            exchange_account=exchange_account,
                            source="order_fill",  # After order execution
                            strategy_version=strategy.id,
                        )
                    )
                    if snapshot:
                        logger.info(
                            f"Created post-rebalance snapshot {snapshot.id} for user {sanitized_user}"
                        )
                    else:
                        logger.warning(
                            f"Failed to create post-rebalance snapshot for user {sanitized_user}"
                        )

            except Exception as e:
                # Don't fail rebalance response if snapshot creation fails
                logger.warning(f"Post-rebalance snapshot creation failed: {e}")

            return Response(
                {
                    "status": "success",
                    "message": f"Rebalance executed successfully. Created {len(created_orders)} orders.",
                    "execution_id": execution.id,
                    "orders_created": len(created_orders),
                    "total_delta": str(execution.total_delta),
                    "nav": str(rebalance_plan.portfolio_nav),
                    "orders": orders_data,
                }
            )

        except Exception as e:
            # Mark execution as failed
            execution.mark_failed(str(e))
            logger.error(
                f"Rebalance execution {execution.id} failed: {e}", exc_info=True
            )

            return Response(
                {
                    "status": "error",
                    "message": "Internal server error occurred during rebalance execution.",
                    "error_code": "EXECUTION_FAILED",
                    "execution_id": execution.id,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except Exception as e:
        logger.error(f"Error in rebalance_execute_view: {e}", exc_info=True)
        return Response(
            {
                "status": "error",
                "message": "Internal server error occurred during rebalance execution",
                "error_code": "REBALANCE_ERROR",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def strategy_constants_view(request):
    """
    Get supported assets and currencies for strategy configuration.

    This endpoint provides the frontend with the list of supported
    quote assets (base currencies) and allocation assets.
    """
    try:
        return Response(
            {
                "status": "success",
                "constants": {
                    "quote_assets": QUOTE_ASSET_SYMBOLS,
                    "allocation_assets": ALL_ALLOCATION_ASSETS,
                },
            },
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        logger.error(f"Error in strategy_constants_view: {e}", exc_info=True)
        return Response(
            {
                "status": "error",
                "message": "Failed to retrieve strategy constants",
                "error_code": "CONSTANTS_ERROR",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
