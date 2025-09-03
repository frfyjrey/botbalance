"""
API views for trading strategies (Step 3: Target Allocation).
"""

import asyncio
import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from botbalance.exchanges.models import ExchangeAccount

from .models import Strategy
from .rebalance_service import rebalance_service
from .serializers import (
    RebalancePlanSerializer,
    StrategyCreateRequestSerializer,
    StrategySerializer,
    StrategyUpdateRequestSerializer,
)

logger = logging.getLogger(__name__)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def user_strategy_view(request):
    """Manage user's trading strategy."""
    try:
        if request.method == "GET":
            return _get_user_strategy(request)
        elif request.method == "POST":
            return _create_or_update_strategy(request)
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
            strategy = strategy_serializer.save()
            return Response(
                {
                    "status": "success",
                    "message": "Strategy updated successfully",
                    "strategy": StrategySerializer(
                        strategy, context={"request": request}
                    ).data,
                }
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
            strategy = strategy_serializer.save()
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
        else:
            return Response(
                {
                    "status": "error",
                    "message": "Failed to create strategy",
                    "errors": strategy_serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def rebalance_plan_view(request):
    """Calculate rebalancing plan for user's strategy."""
    try:
        logger.info(f"Rebalance plan request from user: {request.user}")

        # Get user's strategy
        strategy = Strategy.objects.filter(user=request.user).first()
        logger.info(f"Found strategy: {strategy}")

        if not strategy:
            logger.warning(f"No strategy found for user {request.user}")
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

        plan = asyncio.run(
            rebalance_service.calculate_rebalance_plan(
                strategy, exchange_account, force_refresh
            )
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

        # Convert plan to dict for serialization
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
