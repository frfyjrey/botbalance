"""
API Views for the botbalance project.
"""

from datetime import datetime

import redis
from celery import current_app as celery_app
from celery.result import AsyncResult
from django.conf import settings
from django.db import connection
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from botbalance.tasks.tasks import echo_task, heartbeat_task, long_running_task

from .serializers import (
    LoginSerializer,
    TaskSerializer,
    UserSerializer,
)

# =============================================================================
# AUTHENTICATION VIEWS
# =============================================================================


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """
    User login endpoint.

    Returns JWT access and refresh tokens.
    """
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "status": "success",
                "message": "Login successful",
                "user": UserSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            }
        )

    return Response(
        {"status": "error", "message": "Login failed", "errors": serializer.errors},
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_profile_view(request):
    """
    Get current user profile.
    """
    return Response({"status": "success", "user": UserSerializer(request.user).data})


# =============================================================================
# HEALTH CHECK VIEWS
# =============================================================================


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check_view(request):
    """
    System health check endpoint.

    Checks database, Redis, and Celery connectivity.
    """
    health_data = {
        "status": "healthy",
        "timestamp": datetime.now(),
        "database": {"status": "unknown"},
        "redis": {"status": "unknown"},
        "celery": {"status": "unknown"},
    }

    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            health_data["database"] = {"status": "healthy", "connection": True}
    except Exception as e:
        health_data["database"] = {"status": "unhealthy", "error": str(e)}
        health_data["status"] = "unhealthy"

    # Check Redis
    try:
        redis_client = redis.from_url(settings.CELERY_BROKER_URL)
        redis_client.ping()
        health_data["redis"] = {"status": "healthy", "connection": True}
    except Exception as e:
        health_data["redis"] = {"status": "unhealthy", "error": str(e)}
        health_data["status"] = "unhealthy"

    # Check Celery
    try:
        # Try to inspect Celery workers
        inspect = celery_app.control.inspect()
        stats = inspect.stats()

        if stats:
            health_data["celery"] = {
                "status": "healthy",
                "workers": len(stats),
                "active_workers": list(stats.keys()),
            }
        else:
            health_data["celery"] = {
                "status": "warning",
                "workers": 0,
                "message": "No Celery workers found",
            }
    except Exception as e:
        health_data["celery"] = {"status": "unhealthy", "error": str(e)}

    response_status = (
        status.HTTP_200_OK
        if health_data["status"] == "healthy"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return Response(health_data, status=response_status)


@api_view(["GET"])
@permission_classes([AllowAny])
def version_view(request):
    """
    API version information.
    """
    return Response(
        {
            "name": "BotBalance API",
            "version": "1.0.0",
            "description": "Django + DRF + Celery botbalance API",
            "docs": "/api/docs/",
            "health": "/api/health/",
            "environment": "development" if settings.DEBUG else "production",
            "timestamp": datetime.now(),
        }
    )


# =============================================================================
# TASK MANAGEMENT VIEWS
# =============================================================================


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_echo_task_view(request):
    """
    Create an echo task.

    Returns task ID for status tracking.
    """
    serializer = TaskSerializer(data=request.data)
    if serializer.is_valid():
        message = serializer.validated_data["message"]
        delay = serializer.validated_data.get("delay", 0)

        # Create the task
        task = echo_task.delay(message, delay)

        return Response(
            {
                "status": "success",
                "message": "Task created successfully",
                "task_id": task.id,
                "task_url": f"/api/tasks/status/?task_id={task.id}",
            }
        )

    return Response(
        {
            "status": "error",
            "message": "Invalid task data",
            "errors": serializer.errors,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_heartbeat_task_view(request):
    """
    Create a heartbeat task.
    """
    task = heartbeat_task.delay()

    return Response(
        {
            "status": "success",
            "message": "Heartbeat task created",
            "task_id": task.id,
            "task_url": f"/api/tasks/status/?task_id={task.id}",
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_long_task_view(request):
    """
    Create a long-running task for testing progress tracking.
    """
    duration = request.data.get("duration", 10)
    duration = max(1, min(duration, 60))  # Limit between 1-60 seconds

    task = long_running_task.delay(duration)

    return Response(
        {
            "status": "success",
            "message": f"Long task created (duration: {duration}s)",
            "task_id": task.id,
            "task_url": f"/api/tasks/status/?task_id={task.id}",
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def task_status_view(request):
    """
    Get task status by task_id.
    """
    task_id = request.query_params.get("task_id")

    if not task_id:
        return Response(
            {"status": "error", "message": "task_id parameter is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        result = AsyncResult(task_id, app=celery_app)

        response_data = {
            "task_id": task_id,
            "state": result.state,
            "result": result.result,
            "info": result.info,
            "traceback": result.traceback,
            "successful": result.successful() if result.ready() else None,
            "ready": result.ready(),
        }

        # Add progress info for PROGRESS state
        if result.state == "PROGRESS":
            info = result.info
            if isinstance(info, dict):
                response_data["progress"] = {
                    "current": info.get("current", 0),
                    "total": info.get("total", 1),
                    "percentage": round(
                        (info.get("current", 0) / info.get("total", 1)) * 100, 1
                    ),
                    "status": info.get("status", ""),
                }

        return Response({"status": "success", "task": response_data})

    except Exception as e:
        return Response(
            {"status": "error", "message": f"Failed to get task status: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_tasks_view(request):
    """
    List active tasks (requires Redis inspection).
    """
    try:
        inspect = celery_app.control.inspect()

        active_tasks = inspect.active()
        scheduled_tasks = inspect.scheduled()
        reserved_tasks = inspect.reserved()

        return Response(
            {
                "status": "success",
                "active_tasks": active_tasks or {},
                "scheduled_tasks": scheduled_tasks or {},
                "reserved_tasks": reserved_tasks or {},
                "total_active": sum(
                    len(tasks) for tasks in (active_tasks or {}).values()
                ),
                "timestamp": datetime.now(),
            }
        )

    except Exception as e:
        return Response(
            {"status": "error", "message": f"Failed to list tasks: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# =============================================================================
# EXCHANGE & BALANCES VIEWS
# =============================================================================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_balances_view(request):
    """
    Get user's exchange account balances.

    For MVP: returns balances from user's first active exchange account.
    Later: will support account selection via query params.
    """
    import asyncio
    from decimal import Decimal

    from botbalance.exchanges.models import ExchangeAccount

    try:
        # Get user's first active exchange account
        exchange_account = ExchangeAccount.objects.filter(
            user=request.user, is_active=True
        ).first()

        if not exchange_account:
            return Response(
                {
                    "status": "error",
                    "message": "No active exchange accounts found. Please add an exchange account first.",
                    "error_code": "NO_EXCHANGE_ACCOUNTS",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get adapter and fetch balances
        adapter = exchange_account.get_adapter()
        raw_balances = asyncio.run(adapter.get_balances(exchange_account.account_type))

        # Convert to list format for serializer
        balances_data = []
        total_usd_value = Decimal("0.00")

        for asset, balance in raw_balances.items():
            if balance > 0:  # Only include non-zero balances
                # For MVP: mock USD values (will implement real price calculation in Step 2)
                mock_usd_prices = {
                    "BTC": Decimal("43250.50"),
                    "ETH": Decimal("2580.75"),
                    "BNB": Decimal("310.25"),
                    "USDT": Decimal("1.00"),
                    "USDC": Decimal("1.00"),
                }

                usd_price = mock_usd_prices.get(asset, Decimal("1.00"))
                usd_value = balance * usd_price
                total_usd_value += usd_value

                balances_data.append(
                    {
                        "asset": asset,
                        "balance": balance,
                        "usd_value": usd_value,
                    }
                )

        response_data = {
            "status": "success",
            "exchange_account": exchange_account.name,
            "account_type": exchange_account.account_type,
            "balances": balances_data,
            "total_usd_value": total_usd_value,
            "timestamp": datetime.now(),
        }

        return Response(response_data)

    except Exception as e:
        return Response(
            {
                "status": "error",
                "message": f"Failed to fetch balances: {str(e)}",
                "error_code": "BALANCE_FETCH_ERROR",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
