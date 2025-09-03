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
    CreateSnapshotRequestSerializer,
    CreateSnapshotResponseSerializer,
    LatestSnapshotResponseSerializer,
    LoginSerializer,
    SnapshotListResponseSerializer,
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
        import logging

        logger = logging.getLogger(__name__)
        logger.error("Error getting task status: %s", str(e), exc_info=True)

        return Response(
            {
                "status": "error",
                "message": "Failed to get task status due to an internal error.",
            },
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
        import logging

        logger = logging.getLogger(__name__)
        logger.error("Error listing tasks: %s", str(e), exc_info=True)

        return Response(
            {
                "status": "error",
                "message": "Failed to list tasks due to an internal error.",
            },
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
        import logging

        logger = logging.getLogger(__name__)
        logger.error("Error fetching balances: %s", str(e), exc_info=True)

        return Response(
            {
                "status": "error",
                "message": "Failed to fetch balances due to an internal error.",
                "error_code": "BALANCE_FETCH_ERROR",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def portfolio_summary_view(request):
    """
    Get user's portfolio summary with NAV, asset allocations, and performance data.

    For Step 2: Provides complete portfolio snapshot including:
    - Total Net Asset Value (NAV) in USD
    - Individual asset balances and values
    - Percentage allocation of each asset
    - Price cache statistics and data sources

    Returns 200 with portfolio data or appropriate error response.
    """
    import asyncio
    import logging

    from botbalance.exchanges.models import ExchangeAccount
    from botbalance.exchanges.portfolio_service import portfolio_service

    from .serializers import PortfolioSummaryResponseSerializer

    logger = logging.getLogger(__name__)

    try:
        # Get user's active exchange account
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

        # Calculate portfolio summary
        sanitized_username = (
            request.user.username.replace("\r", "").replace("\n", "")
            if request.user.username
            else ""
        )
        logger.info(f"Calculating portfolio summary for user {sanitized_username}")

        portfolio_summary = asyncio.run(
            portfolio_service.calculate_portfolio_summary(exchange_account)
        )

        if portfolio_summary is None:
            return Response(
                {
                    "status": "error",
                    "message": "Failed to calculate portfolio summary. Please try again later.",
                    "error_code": "PORTFOLIO_CALCULATION_FAILED",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Validate portfolio data
        validation_issues = portfolio_service.validate_portfolio_data(portfolio_summary)
        if validation_issues:
            logger.warning(f"Portfolio validation issues: {validation_issues}")
            # Continue anyway but log the issues

        # Convert to dictionary for serialization
        portfolio_data = {
            "total_nav": portfolio_summary.total_nav,
            "assets": [
                {
                    "symbol": asset.symbol,
                    "balance": asset.balance,
                    "price_usd": asset.price_usd,
                    "value_usd": asset.value_usd,
                    "percentage": asset.percentage,
                    "price_source": asset.price_source,
                }
                for asset in portfolio_summary.assets
            ],
            "quote_currency": portfolio_summary.quote_currency,
            "timestamp": portfolio_summary.timestamp,
            "exchange_account": portfolio_summary.exchange_account,
            "price_cache_stats": portfolio_summary.price_cache_stats,
        }

        # Create portfolio snapshot asynchronously (fire-and-forget with throttling)
        try:
            from threading import Thread

            from botbalance.exchanges.snapshot_service import snapshot_service

            def create_snapshot_async():
                """Create snapshot in background thread."""
                try:
                    snapshot = asyncio.run(
                        snapshot_service.throttled_create_snapshot(
                            user=request.user,
                            exchange_account=exchange_account,
                            source="summary",
                        )
                    )
                    if snapshot:
                        logger.debug(
                            f"Created background snapshot {snapshot.id} for user {request.user.username}"
                        )
                    else:
                        logger.debug(
                            f"Snapshot creation throttled for user {request.user.username}"
                        )
                except Exception as e:
                    logger.warning(
                        f"Background snapshot creation failed for user {request.user.username}: {e}"
                    )

            # Start background thread (non-blocking)
            Thread(target=create_snapshot_async, daemon=True).start()

        except Exception as e:
            # If snapshot creation setup fails, continue with response
            logger.warning(f"Failed to setup background snapshot creation: {e}")

        # Serialize response
        response_data = {
            "status": "success",
            "portfolio": portfolio_data,
        }

        serializer = PortfolioSummaryResponseSerializer(data=response_data)
        if serializer.is_valid():
            logger.info(
                f"Portfolio summary calculated: NAV=${portfolio_summary.total_nav}, "
                f"{len(portfolio_summary.assets)} assets"
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            logger.error(f"Serialization errors: {serializer.errors}")
            return Response(
                {
                    "status": "error",
                    "message": "Failed to serialize portfolio data.",
                    "error_code": "SERIALIZATION_ERROR",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error("Error calculating portfolio summary: %s", str(e), exc_info=True)

        return Response(
            {
                "status": "error",
                "message": "Failed to calculate portfolio summary due to an internal error.",
                "error_code": "PORTFOLIO_SUMMARY_ERROR",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# =============================================================================
# PORTFOLIO SNAPSHOT VIEWS (Step 2)
# =============================================================================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def portfolio_snapshots_list_view(request):
    """
    Get list of user's portfolio snapshots.

    Query parameters:
    - limit: number of snapshots to return (default 10, max 100)
    - from: ISO timestamp to filter snapshots from
    - to: ISO timestamp to filter snapshots to
    """
    import logging
    from datetime import datetime

    from botbalance.exchanges.models import ExchangeAccount
    from botbalance.exchanges.snapshot_service import snapshot_service

    logger = logging.getLogger(__name__)

    try:
        # Parse query parameters
        limit = min(int(request.GET.get("limit", 10)), 100)
        from_ts = request.GET.get("from")
        to_ts = request.GET.get("to")

        # Get user's exchange account
        exchange_account = ExchangeAccount.objects.filter(
            user=request.user, is_active=True
        ).first()

        # Get snapshots
        snapshots = snapshot_service.get_recent_snapshots(
            user=request.user,
            limit=limit + 1,  # Get one extra to check if more exist
            exchange_account=exchange_account,
        )

        # Apply date filters if provided
        if from_ts:
            try:
                from_dt = datetime.fromisoformat(from_ts.replace("Z", "+00:00"))
                snapshots = [s for s in snapshots if s.ts >= from_dt]
            except ValueError:
                return Response(
                    {
                        "status": "error",
                        "message": "Invalid 'from' timestamp format",
                        "error_code": "INVALID_TIMESTAMP",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if to_ts:
            try:
                to_dt = datetime.fromisoformat(to_ts.replace("Z", "+00:00"))
                snapshots = [s for s in snapshots if s.ts <= to_dt]
            except ValueError:
                return Response(
                    {
                        "status": "error",
                        "message": "Invalid 'to' timestamp format",
                        "error_code": "INVALID_TIMESTAMP",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Check if more snapshots available
        has_more = len(snapshots) > limit
        if has_more:
            snapshots = snapshots[:limit]

        # Serialize model instances directly (not data validation)
        response_data = {
            "status": "success",
            "snapshots": snapshots,  # Model instances with all fields (id, ts, created_at)
            "count": len(snapshots),
            "has_more": has_more,
        }

        # Use serializer for output (not validation)
        serializer = SnapshotListResponseSerializer(response_data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(
            f"Error fetching snapshots for user {request.user.username}: {e}",
            exc_info=True,
        )
        return Response(
            {
                "status": "error",
                "message": "Failed to fetch portfolio snapshots",
                "error_code": "SNAPSHOTS_FETCH_ERROR",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_portfolio_snapshot_view(request):
    """
    Create a new portfolio snapshot for the user.
    """
    import asyncio
    import logging

    from botbalance.exchanges.models import ExchangeAccount
    from botbalance.exchanges.snapshot_service import snapshot_service

    logger = logging.getLogger(__name__)

    try:
        # Validate request data
        request_serializer = CreateSnapshotRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            return Response(
                {
                    "status": "error",
                    "message": "Invalid request data",
                    "error_code": "INVALID_REQUEST",
                    "errors": request_serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        force = request_serializer.validated_data["force"]

        # Get user's exchange account
        exchange_account = ExchangeAccount.objects.filter(
            user=request.user, is_active=True
        ).first()

        # Create snapshot
        if force:
            # Force creation bypasses throttling
            snapshot = asyncio.run(
                snapshot_service.create_snapshot(
                    user=request.user,
                    exchange_account=exchange_account,
                    source="summary",
                    force=True,
                )
            )
        else:
            # Use throttled creation
            snapshot = asyncio.run(
                snapshot_service.throttled_create_snapshot(
                    user=request.user,
                    exchange_account=exchange_account,
                    source="summary",
                )
            )

        if snapshot:
            response_data = {
                "status": "success",
                "snapshot": snapshot.to_summary_dict(),
            }
        else:
            # Either throttled or failed
            response_data = {
                "status": "throttled",
                "message": "⏳ Snapshot creation throttled (max 1 per minute). Wait 60 seconds or use 'Force Create'.",
                "error_code": "THROTTLED",
            }

        serializer = CreateSnapshotResponseSerializer(data=response_data)
        if serializer.is_valid():
            response_status = (
                status.HTTP_201_CREATED
                if snapshot
                else status.HTTP_429_TOO_MANY_REQUESTS
            )
            return Response(serializer.data, status=response_status)
        else:
            logger.error(f"Serialization errors: {serializer.errors}")
            return Response(
                {
                    "status": "error",
                    "message": "Failed to serialize response",
                    "error_code": "SERIALIZATION_ERROR",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except Exception as e:
        logger.error(
            f"Error creating snapshot for user {request.user.username}: {e}",
            exc_info=True,
        )
        return Response(
            {
                "status": "error",
                "message": "Failed to create portfolio snapshot",
                "error_code": "SNAPSHOT_CREATION_ERROR",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def latest_portfolio_snapshot_view(request):
    """
    Get user's latest portfolio snapshot with full details.
    """
    import logging

    from botbalance.exchanges.models import ExchangeAccount
    from botbalance.exchanges.snapshot_service import snapshot_service

    logger = logging.getLogger(__name__)

    try:
        # Get user's exchange account
        exchange_account = ExchangeAccount.objects.filter(
            user=request.user, is_active=True
        ).first()

        # Get latest snapshot
        snapshot = snapshot_service.get_latest_snapshot(
            user=request.user, exchange_account=exchange_account
        )

        if snapshot:
            snapshot_data = {
                "id": snapshot.id,
                "ts": snapshot.ts.isoformat(),
                "quote_asset": snapshot.quote_asset,
                "nav_quote": str(snapshot.nav_quote),
                "asset_count": snapshot.get_asset_count(),
                "source": snapshot.source,
                "exchange_account": snapshot.exchange_account.name
                if snapshot.exchange_account
                else None,
                "created_at": snapshot.created_at.isoformat(),
                "positions": snapshot.positions,
                "prices": snapshot.prices,
            }

            response_data = {
                "status": "success",
                "snapshot": snapshot_data,
            }
        else:
            response_data = {
                "status": "not_found",
                "message": "No portfolio snapshots found for this user",
                "error_code": "NO_SNAPSHOTS",
            }

        serializer = LatestSnapshotResponseSerializer(data=response_data)
        if serializer.is_valid():
            response_status = (
                status.HTTP_200_OK if snapshot else status.HTTP_404_NOT_FOUND
            )
            return Response(serializer.data, status=response_status)
        else:
            logger.error(f"Serialization errors: {serializer.errors}")
            return Response(
                {
                    "status": "error",
                    "message": "Failed to serialize snapshot data",
                    "error_code": "SERIALIZATION_ERROR",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except Exception as e:
        logger.error(
            f"Error fetching latest snapshot for user {request.user.username}: {e}",
            exc_info=True,
        )
        return Response(
            {
                "status": "error",
                "message": "Failed to fetch latest portfolio snapshot",
                "error_code": "LATEST_SNAPSHOT_ERROR",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_all_portfolio_snapshots_view(request):
    """
    Delete all portfolio snapshots for the user (for testing purposes).
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Count existing snapshots
        snapshot_count = request.user.portfolio_snapshots.count()

        if snapshot_count == 0:
            return Response(
                {
                    "status": "success",
                    "message": "No snapshots to delete",
                    "deleted_count": 0,
                },
                status=status.HTTP_200_OK,
            )

        # Delete all snapshots for the user
        deleted_count, _ = request.user.portfolio_snapshots.all().delete()

        logger.info(
            f"Deleted {deleted_count} snapshots for user {request.user.username}"
        )

        return Response(
            {
                "status": "success",
                "message": f"Successfully deleted {deleted_count} portfolio snapshots",
                "deleted_count": deleted_count,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        logger.error(
            f"Error deleting snapshots for user {request.user.username}: {e}",
            exc_info=True,
        )
        return Response(
            {
                "status": "error",
                "message": "Failed to delete portfolio snapshots",
                "error_code": "DELETE_SNAPSHOTS_ERROR",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
