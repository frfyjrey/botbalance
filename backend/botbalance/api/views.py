"""
API Views for the botbalance project.
"""

from datetime import datetime
from typing import cast

import redis
from celery import current_app as celery_app
from celery.result import AsyncResult
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connection
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from botbalance.exchanges.models import ExchangeAccount, PortfolioState
from botbalance.tasks.tasks import echo_task, heartbeat_task, long_running_task
from strategies.models import Order

from .serializers import (
    CreateSnapshotRequestSerializer,
    CreateSnapshotResponseSerializer,
    LatestSnapshotResponseSerializer,
    LoginSerializer,
    PortfolioStateResponseSerializer,
    RefreshStateRequestSerializer,
    RefreshStateResponseSerializer,
    SnapshotListResponseSerializer,
    TaskSerializer,
    UserSerializer,
)


def sanitize_for_logs(text: str) -> str:
    """
    Sanitize text for safe logging by removing control characters.

    Prevents log injection attacks by removing newlines and carriage returns.
    """
    if not text:
        return ""
    return str(text).replace("\r\n", "").replace("\n", "").replace("\r", "")


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
    import logging
    from decimal import Decimal

    from botbalance.exchanges.models import ExchangeAccount

    logger = logging.getLogger(__name__)

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

        # Get balances with fallback to snapshot data
        # Try live calculation first
        from botbalance.exchanges.portfolio_service import portfolio_service

        portfolio_summary = asyncio.run(
            portfolio_service.calculate_portfolio_summary(exchange_account)
        )

        # If live calculation failed, try fallback to latest snapshot
        if portfolio_summary is None:
            logger.warning(
                "Balance calculation returned None, trying fallback to latest snapshot"
            )

            # Fallback: try to get data from latest snapshot
            from botbalance.exchanges.snapshot_service import snapshot_service

            latest_snapshot = snapshot_service.get_latest_snapshot(
                user=request.user, exchange_account=exchange_account
            )

            if latest_snapshot:
                logger.info(
                    f"Using fallback snapshot {latest_snapshot.id} for balances"
                )
                # Convert snapshot to portfolio summary format
                portfolio_summary = _convert_snapshot_to_portfolio_summary(
                    latest_snapshot
                )
                # Extract raw balances from snapshot
                raw_balances = {
                    symbol: Decimal(str(position["amount"]))
                    for symbol, position in latest_snapshot.positions.items()
                }
            else:
                logger.error("No snapshots available for fallback")
                portfolio_summary = None
                raw_balances = {}
        else:
            # Live calculation succeeded, get raw balances normally
            adapter = exchange_account.get_adapter()
            raw_balances = asyncio.run(
                adapter.get_balances(exchange_account.account_type)
            )

        if portfolio_summary is None:
            return Response(
                {
                    "status": "error",
                    "message": "Unable to fetch balances and no previous data available. This may be due to external API issues.",
                    "error_code": "BALANCE_FETCH_ERROR",
                    "details": {
                        "suggestion": "Please try again in a few minutes. The issue may be with external exchange APIs.",
                        "fallback_attempted": True,
                    },
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Map assets to values for response
        value_map: dict[str, Decimal] = {
            asset.symbol: asset.value_usd for asset in portfolio_summary.assets
        }

        # Use same whitelist as portfolio service for consistency (Top ~200 from CoinMarketCap)
        ALLOWED_ASSETS = {
            # Top 10 Major cryptocurrencies
            "BTC",
            "ETH",
            "USDT",
            "BNB",
            "SOL",
            "XRP",
            "USDC",
            "ADA",
            "DOGE",
            "AVAX",
            # Top 11-50
            "LINK",
            "DOT",
            "MATIC",
            "TRX",
            "ICP",
            "SHIB",
            "UNI",
            "LTC",
            "BCH",
            "NEAR",
            "APT",
            "LEO",
            "DAI",
            "ATOM",
            "XMR",
            "ETC",
            "VET",
            "FIL",
            "HBAR",
            "TAO",
            "ARB",
            "IMX",
            "OP",
            "MKR",
            "INJ",
            "AAVE",
            "GRT",
            "THETA",
            "LDO",
            "RUNE",
            "STX",
            "FTM",
            "ALGO",
            "XTZ",
            "EGLD",
            "FLOW",
            "SAND",
            "MANA",
            "APE",
            "CRV",
            # Top 51-100
            "SNX",
            "CAKE",
            "SUSHI",
            "COMP",
            "YFI",
            "BAL",
            "1INCH",
            "ENJ",
            "GALA",
            "CHZ",
            "ZIL",
            "MINA",
            "KAVA",
            "ONE",
            "ROSE",
            "CELO",
            "ANKR",
            "REN",
            "OCEAN",
            "NMR",
            "FET",
            "KSM",
            "WAVES",
            "ICX",
            "ZEC",
            "DASH",
            "DCR",
            "QTUM",
            "BAT",
            "SC",
            "STORJ",
            "REP",
            "KNC",
            "LRC",
            "BNT",
            "MLN",
            "GNO",
            "RLC",
            "MAID",
            "ANT",
            # Top 101-150
            "HOT",
            "DENT",
            "WIN",
            "BTT",
            "TWT",
            "SFP",
            "DYDX",
            "GMX",
            "PERP",
            "LOOKS",
            "BLUR",
            "MAGIC",
            "RDNT",
            "JOE",
            "PYR",
            "GOVI",
            "SPELL",
            "TRIBE",
            "BADGER",
            "RARI",
            "MASK",
            "ALPHA",
            "BETA",
            "FARM",
            "CREAM",
            "HEGIC",
            "PICKLE",
            "COVER",
            "VALUE",
            "ARMOR",
            "SAFE",
            "DPI",
            "INDEX",
            "FLI",
            "MVI",
            "BED",
            "DATA",
            "GMI",
            # Layer 2 & Scaling
            "METIS",
            "BOBA",
            "STRK",
            # Exchange Tokens
            "FTT",
            "CRO",
            "HT",
            "OKB",
            "KCS",
            "GT",
            # Stablecoins
            "BUSD",
            "TUSD",
            "USDD",
            "FRAX",
            "MIM",
            "LUSD",
            "USDP",
            "GUSD",
            "HUSD",
            "RSV",
            "NUSD",
            "DUSD",
            "ALUSD",
            "OUSD",
            "USDX",
            "CUSD",
            "EURS",
            # DeFi Protocols
            # Gaming & NFT
            "AXS",
            "SLP",
            "ILV",
            "ALICE",
            "TLM",
            "NFTX",
            "TREASURE",
            "PRIME",
            "GHST",
            # Oracle & Infrastructure
            "BAND",
            "TRB",
            "API3",
            "DIA",
            "UMA",
            "NEST",
            "FLUX",
            "PYTH",
            # Meme Coins
            "FLOKI",
            "PEPE",
            "BONK",
            "WIF",
            "DEGEN",
            "BOME",
            "MEME",
            # New & Trending (2023-2024)
            "SUI",
            "SEI",
            "TIA",
            "JTO",
            "WLD",
            "JUP",
            "ONDO",
            "MANTA",
            "ALT",
            "AEVO",
            "PIXEL",
            "PORTAL",
            "AXL",
            # Additional Popular Tokens
            "HOOK",
            "POLYX",
            "LEVER",
            "HFT",
            "DUSK",
            "HIGH",
            "CVX",
            "FXS",
            "OHM",
            "ICE",
            "BICO",
            "POLS",
            "DF",
            "TVK",
            "SUPER",
            "GODS",
            "DPET",
            "WILD",
        }

        balances_data = []
        total_usd_value = portfolio_summary.total_nav

        for asset, balance in raw_balances.items():
            if (
                balance > 0 and asset.upper() in ALLOWED_ASSETS
            ):  # Added whitelist filter
                usd_value = value_map.get(asset, Decimal("0.00"))
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
    [DEPRECATED] Get user's portfolio summary with NAV, asset allocations, and performance data.

    ⚠️  DEPRECATED: This endpoint is being phased out in favor of PortfolioState architecture.
    ⚠️  Use the new endpoints instead:
    ⚠️    - GET /api/me/portfolio/state/ - for current portfolio state (faster)
    ⚠️    - POST /api/me/portfolio/state/refresh/ - for manual refresh

    Legacy endpoint for Step 2: Provides complete portfolio snapshot including:
    - Total Net Asset Value (NAV) in USD
    - Individual asset balances and values
    - Percentage allocation of each asset
    - Price cache statistics and data sources

    Returns 200 with portfolio data or appropriate error response.

    NOTE: As of Step 5, this endpoint no longer creates portfolio snapshots.
    """
    import asyncio
    import logging

    from botbalance.exchanges.models import ExchangeAccount
    from botbalance.exchanges.portfolio_service import portfolio_service

    from .serializers import PortfolioSummaryResponseSerializer

    logger = logging.getLogger(__name__)

    # DEPRECATION WARNING
    logger.warning(
        f"User {sanitize_for_logs(request.user.username)} is using deprecated /portfolio/summary endpoint. "
        "Consider migrating to /portfolio/state/ for better performance."
    )

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

        # Calculate portfolio summary with fallback to latest snapshot
        sanitized_username = (
            request.user.username.replace("\r", "").replace("\n", "")
            if request.user.username
            else ""
        )
        logger.info(f"Calculating portfolio summary for user {sanitized_username}")

        portfolio_summary = asyncio.run(
            portfolio_service.calculate_portfolio_summary(exchange_account)
        )

        # Track if we're using fallback data
        using_fallback = False
        fallback_age_minutes = 0

        # If live calculation failed, try fallback to latest snapshot
        if portfolio_summary is None:
            # Throttle repeated warnings (only log every 5 minutes per user)
            cache_key = (
                f"portfolio_fallback_warning_{request.user.id}_{exchange_account.id}"
            )
            from django.core.cache import cache

            if not cache.get(cache_key):
                logger.warning(
                    "Portfolio calculation returned None, trying fallback to latest snapshot"
                )
                cache.set(cache_key, True, 300)  # Cache for 5 minutes

            # Fallback: try to get data from latest snapshot
            from botbalance.exchanges.snapshot_service import snapshot_service

            latest_snapshot = snapshot_service.get_latest_snapshot(
                user=request.user, exchange_account=exchange_account
            )

            if latest_snapshot:
                from datetime import datetime

                fallback_age_minutes = int(
                    (
                        datetime.now(latest_snapshot.ts.tzinfo) - latest_snapshot.ts
                    ).total_seconds()
                    / 60
                )
                if not cache.get(cache_key):
                    logger.info(
                        f"Using fallback snapshot {latest_snapshot.id} from {latest_snapshot.ts} ({fallback_age_minutes}min old)"
                    )
                # Convert snapshot to portfolio summary format
                portfolio_summary = _convert_snapshot_to_portfolio_summary(
                    latest_snapshot
                )
                using_fallback = True
            else:
                logger.error("No snapshots available for fallback")

        if portfolio_summary is None:
            return Response(
                {
                    "status": "error",
                    "message": "Unable to calculate portfolio summary and no previous data available. This may be due to external API issues.",
                    "error_code": "PORTFOLIO_CALCULATION_FAILED",
                    "details": {
                        "suggestion": "Please try again in a few minutes. The issue may be with external exchange APIs.",
                        "fallback_attempted": True,
                    },
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
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

        # NOTE: Snapshot creation removed as part of PortfolioState migration (Step 5)
        # Snapshots are now created from PortfolioState in dedicated endpoints
        logger.debug(
            f"Legacy summary endpoint used by {sanitize_for_logs(request.user.username)}, "
            f"using_fallback={using_fallback}, no snapshot created"
        )

        # Serialize response
        response_data = {
            "status": "success",
            "portfolio": portfolio_data,
            "exchange_account": {
                "id": exchange_account.id,
                "name": exchange_account.name,
                "exchange": exchange_account.exchange,
                "account_type": exchange_account.account_type,
                "testnet": exchange_account.testnet,
                "is_active": exchange_account.is_active,
            },
            # exchange_status removed - replaced by simple health fields in ExchangeAccount model
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
            f"Error fetching snapshots for user {sanitize_for_logs(request.user.username)}: {e}",
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
            f"Error creating snapshot for user {sanitize_for_logs(request.user.username)}: {e}",
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
            f"Error fetching latest snapshot for user {sanitize_for_logs(request.user.username)}: {e}",
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
            f"Deleted {deleted_count} snapshots for user {sanitize_for_logs(request.user.username)}"
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
            f"Error deleting snapshots for user {sanitize_for_logs(request.user.username)}: {e}",
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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_orders_view(request):
    """
    Get user's orders with filtering and pagination.

    Query parameters:
    - limit: Number of orders to return (default: 50, max: 200)
    - offset: Offset for pagination (default: 0)
    - status: Filter by order status (pending, submitted, open, filled, cancelled, rejected, failed)
    - symbol: Filter by trading symbol (e.g., 'BTCUSDT')
    - side: Filter by order side (buy, sell)
    - exchange: Filter by exchange (binance, okx)

    Returns:
    - orders: List of user orders
    - total: Total number of orders (without limit/offset)
    - has_more: Whether there are more orders available
    """
    try:
        # Parse query parameters
        limit = min(
            int(request.GET.get("limit", 50)), 200
        )  # Max 200 orders per request
        offset = max(int(request.GET.get("offset", 0)), 0)
        status_filter = request.GET.get("status")
        symbol_filter = request.GET.get("symbol")
        side_filter = request.GET.get("side")
        exchange_filter = request.GET.get("exchange")

        # Build query
        orders_qs = Order.objects.filter(user=request.user)

        if status_filter:
            orders_qs = orders_qs.filter(status=status_filter)
        if symbol_filter:
            orders_qs = orders_qs.filter(symbol__iexact=symbol_filter)
        if side_filter:
            orders_qs = orders_qs.filter(side=side_filter)
        if exchange_filter:
            orders_qs = orders_qs.filter(exchange=exchange_filter)

        # Get total count
        total_count = orders_qs.count()

        # Apply pagination
        orders = orders_qs.select_related("strategy", "execution")[
            offset : offset + limit
        ]

        # Prepare response data
        orders_data = []
        for order in orders:
            orders_data.append(
                {
                    "id": order.id,
                    "exchange_order_id": order.exchange_order_id,
                    "client_order_id": order.client_order_id,
                    "exchange": order.exchange,
                    "symbol": order.symbol,
                    "side": order.side,
                    "status": order.status,
                    "limit_price": str(order.limit_price),
                    "quote_amount": str(order.quote_amount),
                    "filled_amount": str(order.filled_amount),
                    "fill_percentage": str(order.fill_percentage),
                    "fee_amount": str(order.fee_amount),
                    "fee_asset": order.fee_asset,
                    "created_at": order.created_at.isoformat(),
                    "submitted_at": order.submitted_at.isoformat()
                    if order.submitted_at
                    else None,
                    "filled_at": order.filled_at.isoformat()
                    if order.filled_at
                    else None,
                    "updated_at": order.updated_at.isoformat(),
                    "error_message": order.error_message,
                    "strategy_name": order.strategy.name if order.strategy else None,
                    "execution_id": order.execution.id if order.execution else None,
                    "is_active": order.is_active,
                }
            )

        has_more = offset + limit < total_count

        return Response(
            {
                "status": "success",
                "orders": orders_data,
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
            }
        )

    except ValueError:
        return Response(
            {
                "status": "error",
                "message": "Invalid query parameter",
                "error_code": "INVALID_PARAMETER",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error in user_orders_view: {e}", exc_info=True)

        return Response(
            {
                "status": "error",
                "message": "Failed to fetch orders",
                "error_code": "ORDERS_FETCH_ERROR",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_order_view(request, order_id: int):
    """
    Cancel specific user order by our Order.id or exchange_order_id.
    """
    import asyncio

    from botbalance.exchanges.models import ExchangeAccount

    try:
        # Load user's order
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response(
                {
                    "status": "error",
                    "message": "Order not found",
                    "error_code": "ORDER_NOT_FOUND",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Resolve account and adapter - use the same exchange where order was placed
        exchange_account = ExchangeAccount.objects.filter(
            user=request.user,
            exchange=order.exchange,  # Match the exchange where order was placed
            is_active=True,
        ).first()
        if not exchange_account:
            return Response(
                {
                    "status": "error",
                    "message": f"No active {order.exchange} account found. Order was placed on {order.exchange} but you don't have an active account for this exchange.",
                    "error_code": "EXCHANGE_ACCOUNT_MISMATCH",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        adapter = exchange_account.get_adapter()
        # Prefer client_order_id for idempotent cancel, fallback to exchange id
        target_id = order.client_order_id or order.exchange_order_id
        if not target_id:
            return Response(
                {
                    "status": "error",
                    "message": "Order has no identifiers for cancellation",
                    "error_code": "ORDER_NO_IDENTIFIERS",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ok = asyncio.run(adapter.cancel_order(str(target_id), account="spot"))
            if ok:
                order.mark_cancelled()
                return Response({"status": "success", "order_id": order.id})
            return Response(
                {
                    "status": "error",
                    "message": "Cancellation failed",
                    "error_code": "CANCEL_FAILED",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as cancel_error:
            # Handle specific exchange errors
            from botbalance.exchanges.exceptions import FeatureNotEnabledError

            if isinstance(cancel_error, FeatureNotEnabledError):
                return Response(
                    {
                        "status": "error",
                        "message": f"Order cancellation not supported on {order.exchange}",
                        "error_code": "FEATURE_NOT_SUPPORTED",
                        "details": str(cancel_error),
                    },
                    status=status.HTTP_501_NOT_IMPLEMENTED,
                )

            # Re-raise for general exception handler
            raise cancel_error
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"cancel_order_view failed: {e}", exc_info=True)
        return Response(
            {"status": "error", "message": "Internal error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_all_orders_view(request):
    """
    Cancel all open orders for a symbol (optional symbol param required).
    """
    import asyncio

    from botbalance.exchanges.models import ExchangeAccount

    try:
        symbol = request.GET.get("symbol")
        if not symbol:
            return Response(
                {
                    "status": "error",
                    "message": "Query param 'symbol' is required",
                    "error_code": "SYMBOL_REQUIRED",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        exchange_account = ExchangeAccount.objects.filter(
            user=request.user, is_active=True
        ).first()
        if not exchange_account:
            return Response(
                {
                    "status": "error",
                    "message": "No active exchange accounts",
                    "error_code": "NO_EXCHANGE_ACCOUNTS",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        adapter = exchange_account.get_adapter()
        cancelled_count = asyncio.run(
            adapter.cancel_open_orders(symbol.upper(), account="spot")
        )
        return Response({"status": "success", "cancelled": cancelled_count})
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"cancel_all_orders_view failed: {e}", exc_info=True)
        return Response(
            {"status": "error", "message": "Internal error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# =============================================================================
# EXCHANGE ACCOUNTS MANAGEMENT VIEWS
# =============================================================================


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def exchange_accounts_view(request):
    """
    List all user's exchange accounts or create a new one.

    GET: Returns list of user's exchange accounts (excluding sensitive data)
    POST: Creates new exchange account for user
    """
    from botbalance.exchanges.models import ExchangeAccount

    from .serializers import ExchangeAccountSerializer

    if request.method == "GET":
        # List user's exchange accounts
        accounts = ExchangeAccount.objects.filter(user=request.user).order_by(
            "-created_at"
        )
        serializer = ExchangeAccountSerializer(accounts, many=True)

        return Response({"status": "success", "accounts": serializer.data})

    elif request.method == "POST":
        # Create new exchange account
        data = request.data.copy()
        data["user"] = request.user.id

        serializer = ExchangeAccountSerializer(data=data)
        if serializer.is_valid():
            try:
                account = serializer.save(user=request.user)
                return Response(
                    {
                        "status": "success",
                        "message": "Exchange account created successfully",
                        "account": ExchangeAccountSerializer(account).data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            except ValidationError as e:
                return Response(
                    {
                        "status": "error",
                        "message": "Validation failed",
                        "errors": e.message_dict
                        if hasattr(e, "message_dict")
                        else str(e),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {
                    "status": "error",
                    "message": "Invalid data",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def exchange_account_detail_view(request, account_id):
    """
    Get, update or delete a specific exchange account.

    GET: Returns account details
    PUT: Updates account
    DELETE: Deletes account
    """
    from botbalance.exchanges.models import ExchangeAccount

    from .serializers import ExchangeAccountSerializer

    try:
        account = ExchangeAccount.objects.get(id=account_id, user=request.user)
    except ExchangeAccount.DoesNotExist:
        return Response(
            {"status": "error", "message": "Exchange account not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        serializer = ExchangeAccountSerializer(account)
        return Response({"status": "success", "account": serializer.data})

    elif request.method == "PUT":
        data = request.data.copy()
        # Don't allow changing user
        data.pop("user", None)

        serializer = ExchangeAccountSerializer(account, data=data, partial=True)
        if serializer.is_valid():
            try:
                updated_account = serializer.save()
                return Response(
                    {
                        "status": "success",
                        "message": "Exchange account updated successfully",
                        "account": ExchangeAccountSerializer(updated_account).data,
                    }
                )
            except ValidationError as e:
                return Response(
                    {
                        "status": "error",
                        "message": "Validation failed",
                        "errors": e.message_dict
                        if hasattr(e, "message_dict")
                        else str(e),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {
                    "status": "error",
                    "message": "Invalid data",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    elif request.method == "DELETE":
        account_name = account.name
        account.delete()
        return Response(
            {
                "status": "success",
                "message": f"Exchange account '{account_name}' deleted successfully",
            }
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def check_exchange_account_view(request, account_id):
    """
    Perform lightweight health check on exchange account.

    Makes 2 quick API calls:
    1. Public /api/v3/time endpoint (without auth)
    2. Signed /api/v3/openOrders?limit=1 endpoint (with auth)

    Updates health fields and returns status with latency metrics.
    Does not calculate portfolio state or prices.
    """
    import asyncio
    import time
    from concurrent.futures import ThreadPoolExecutor

    from asgiref.sync import sync_to_async
    from django.utils import timezone

    from botbalance.exchanges.models import ExchangeAccount

    try:
        account = ExchangeAccount.objects.get(id=account_id, user=request.user)
    except ExchangeAccount.DoesNotExist:
        return Response(
            {"status": "error", "message": "Exchange account not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    async def perform_health_check():
        """Perform the actual health check with timing."""
        start_time = time.time()

        try:
            adapter = account.get_adapter()

            # 1. Public endpoint test - get server time (no auth required)
            public_start = time.time()
            public_success = False
            public_error = None
            try:
                await adapter.get_server_time()
                public_ms = int((time.time() - public_start) * 1000)
                public_success = True
            except Exception as e:
                public_ms = int((time.time() - public_start) * 1000)
                public_error = str(e)

            # 2. Signed endpoint test - get open orders with limit (requires auth)
            signed_start = time.time()
            signed_success = False
            signed_error = None
            try:
                # Get open orders - limit is handled internally by adapter
                await adapter.get_open_orders()
                signed_ms = int((time.time() - signed_start) * 1000)
                signed_success = True
            except Exception as e:
                signed_ms = int((time.time() - signed_start) * 1000)
                signed_error = str(e)

            total_latency = int((time.time() - start_time) * 1000)

            # Determine overall status
            if public_success and signed_success:
                status_result = "healthy"
                await sync_to_async(account.update_health_success)(total_latency)
            elif public_success and not signed_success:
                if signed_error and (
                    "API-key" in signed_error
                    or "signature" in signed_error
                    or "Invalid API" in signed_error
                ):
                    status_result = "auth_error"
                    await sync_to_async(account.update_health_error)("AUTH_ERROR")
                elif signed_error and (
                    "rate limit" in signed_error.lower() or "429" in signed_error
                ):
                    status_result = "rate_limited"
                    await sync_to_async(account.update_health_error)("RATE_LIMITED")
                else:
                    status_result = "down"
                    await sync_to_async(account.update_health_error)("API_ERROR")
            elif not public_success:
                if public_error and "timeout" in public_error.lower():
                    status_result = "down"
                    await sync_to_async(account.update_health_error)("TIMEOUT")
                elif abs(time.time() - start_time) > 30:  # Simple time skew check
                    status_result = "time_skew"
                    await sync_to_async(account.update_health_error)("TIME_SKEW")
                else:
                    status_result = "down"
                    await sync_to_async(account.update_health_error)("NETWORK_ERROR")
            else:
                status_result = "down"
                await sync_to_async(account.update_health_error)("DOWN")

            return {
                "status": status_result,
                "public_ms": public_ms if public_success else None,
                "signed_ms": signed_ms if signed_success else None,
                "total_latency_ms": total_latency,
                "checked_at": timezone.now().isoformat(),
                "public_success": public_success,
                "signed_success": signed_success,
                "public_error": public_error if not public_success else None,
                "signed_error": signed_error if not signed_success else None,
            }

        except Exception as e:
            # Catastrophic failure
            total_latency = int((time.time() - start_time) * 1000)
            await sync_to_async(account.update_health_error)("CRITICAL_ERROR")
            return {
                "status": "down",
                "public_ms": None,
                "signed_ms": None,
                "total_latency_ms": total_latency,
                "checked_at": timezone.now().isoformat(),
                "error": str(e),
            }

    def run_async_in_thread():
        """Run async code in a new thread with fresh event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(perform_health_check())
        finally:
            loop.close()

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_async_in_thread)
            result = future.result(timeout=30)  # 30 second timeout

        return Response(
            {
                "status": "success",
                "connector_id": account.id,
                "connector_name": account.name,
                "health_check": result,
            }
        )

    except TimeoutError:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Health check timeout for account {account_id}")

        account.update_health_error("TIMEOUT")
        return Response(
            {
                "status": "error",
                "message": "Health check timeout (30 seconds)",
                "connector_id": account.id,
            },
            status=status.HTTP_408_REQUEST_TIMEOUT,
        )
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Health check failed for account {account_id}: {e}")

        account.update_health_error("CHECK_FAILED")
        return Response(
            {
                "status": "error",
                "message": f"Health check failed: {str(e)}",
                "connector_id": account.id,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _convert_snapshot_to_portfolio_summary(snapshot):
    """
    Convert PortfolioSnapshot to PortfolioSummary format for fallback scenarios.

    Used when live portfolio calculation fails and we need to return
    data from the latest successful snapshot.
    """
    from datetime import datetime
    from decimal import ROUND_HALF_UP, Decimal

    from botbalance.exchanges.portfolio_service import PortfolioAsset, PortfolioSummary

    # Convert snapshot positions to PortfolioAsset objects
    assets = []
    total_nav = Decimal(str(snapshot.nav_quote))

    # Round total_nav to 2 decimal places for serializer
    total_nav = total_nav.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    for symbol, position_data in snapshot.positions.items():
        balance = Decimal(str(position_data["amount"]))
        value_usd = Decimal(str(position_data["quote_value"]))

        # Calculate price from amount and value
        price_usd = value_usd / balance if balance > 0 else Decimal("0")
        # Round price_usd to max 18 decimal places
        price_usd = price_usd.quantize(Decimal("0." + "0" * 18), rounding=ROUND_HALF_UP)

        # Calculate percentage and limit to max 5 digits total (XXX.X format)
        if total_nav > 0:
            percentage = value_usd / total_nav * 100
            # Limit to 3 digits before decimal, 1 after (XXX.X max)
            percentage = min(percentage, Decimal("999.9"))
            percentage = percentage.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        else:
            percentage = Decimal("0.0")

        # Round value_usd to 2 decimal places
        value_usd = value_usd.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        asset = PortfolioAsset(
            symbol=symbol,
            balance=balance,
            price_usd=price_usd,
            value_usd=value_usd,
            percentage=percentage,
            price_source="snapshot_fallback",  # Mark as fallback data
        )
        assets.append(asset)

    # Sort assets by value descending
    assets.sort(key=lambda a: a.value_usd, reverse=True)

    # Create PortfolioSummary object with proper price_cache_stats structure
    portfolio_summary = PortfolioSummary(
        total_nav=total_nav,
        assets=assets,
        quote_currency=snapshot.quote_asset,
        timestamp=snapshot.ts,  # Use datetime object, not isoformat string
        exchange_account=snapshot.exchange_account.name
        if snapshot.exchange_account
        else "Unknown",
        price_cache_stats={
            "cache_backend": "snapshot_fallback",  # Required field
            "default_ttl": 0,  # Required field - no TTL for snapshot data
            "stale_threshold": 0,  # Required field - snapshot is already stale
            "supported_quotes": ["USDT", "USD", "USDC", "BUSD"],  # Required field
            "cached_count": len(assets),
            "fresh_count": 0,
            "mock_count": 0,
            "stablecoin_count": len(
                [
                    a
                    for a in assets
                    if a.symbol in ["USDT", "USDC", "BUSD", "DAI", "TUSD"]
                ]
            ),
            "fallback_used": True,  # Indicate this is fallback data
            "snapshot_age_minutes": int(
                (datetime.now(snapshot.ts.tzinfo) - snapshot.ts).total_seconds() / 60
            ),
        },
    )

    return portfolio_summary


# =============================================================================
# PORTFOLIO STATE VIEWS (Etap 4)
# =============================================================================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def portfolio_state_view(request):
    """
    Get current portfolio state for user's exchange account.

    Fast read-only endpoint that returns the current PortfolioState without
    making any API calls to exchanges. Returns 404 if state doesn't exist.

    Query parameters:
    - connector_id (optional): Exchange account ID. If not provided, uses user's active account

    Returns:
    - 200: Portfolio state data
    - 404: ERROR_NO_STATE - state not found for connector
    - 403: Connector doesn't belong to user
    - 400: Multiple active connectors (need to specify connector_id)
    """
    import logging

    from botbalance.exchanges.models import ExchangeAccount

    logger = logging.getLogger(__name__)

    try:
        # Get connector_id parameter
        connector_id = request.query_params.get("connector_id")

        if connector_id:
            # Validate connector belongs to user
            try:
                exchange_account = ExchangeAccount.objects.get(
                    id=connector_id, user=request.user
                )
            except ExchangeAccount.DoesNotExist:
                return Response(
                    {
                        "status": "error",
                        "message": "Exchange account not found or doesn't belong to you",
                        "error_code": "CONNECTOR_NOT_FOUND",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        else:
            # Auto-select user's active exchange account
            active_accounts = ExchangeAccount.objects.filter(
                user=request.user, is_active=True
            )

            if not active_accounts.exists():
                return Response(
                    {
                        "status": "error",
                        "message": "No active exchange accounts found",
                        "error_code": "NO_ACTIVE_CONNECTORS",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
            elif active_accounts.count() > 1:
                return Response(
                    {
                        "status": "error",
                        "message": f"Multiple active exchange accounts found ({active_accounts.count()}). Please specify connector_id parameter.",
                        "error_code": "MULTIPLE_ACTIVE_CONNECTORS",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            exchange_account = cast(
                "ExchangeAccount", active_accounts.first()
            )  # Guaranteed by count() == 1 check above

        # Get PortfolioState for the connector
        try:
            portfolio_state = PortfolioState.objects.get(
                exchange_account=exchange_account
            )
        except PortfolioState.DoesNotExist:
            return Response(
                {
                    "status": "error",
                    "message": f"Portfolio state not found for connector '{exchange_account.name}'",
                    "error_code": "ERROR_NO_STATE",
                    "connector_id": exchange_account.id,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Convert to API response format
        if portfolio_state is None:  # mypy safety check
            return Response(
                {
                    "status": "error",
                    "message": "Portfolio state not found",
                    "error_code": "ERROR_NO_STATE",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        state_data = portfolio_state.to_summary_dict()

        response_data = {
            "status": "success",
            "state": state_data,
        }

        serializer = PortfolioStateResponseSerializer(data=response_data)
        if serializer.is_valid():
            logger.info(
                f"Portfolio state retrieved for user {sanitize_for_logs(request.user.username)}, "
                f"connector {exchange_account.name}"
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            logger.error(f"Serialization errors: {serializer.errors}")
            return Response(
                {
                    "status": "error",
                    "message": "Failed to serialize state data",
                    "error_code": "SERIALIZATION_ERROR",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in portfolio_state_view: {e}", exc_info=True)

        return Response(
            {
                "status": "error",
                "message": "Failed to get portfolio state due to an internal error",
                "error_code": "PORTFOLIO_STATE_ERROR",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def refresh_portfolio_state_view(request):
    """
    Force refresh/create portfolio state for user's exchange account.

    Makes API calls to exchange and updates the PortfolioState. Can fail with
    various error codes based on the state calculation result.

    Request body:
    - connector_id (optional): Exchange account ID

    Returns:
    - 200: State refreshed successfully
    - 409: NO_ACTIVE_STRATEGY - no active strategy for connector
    - 422: ERROR_PRICING - unable to get prices for some assets
    - 429: TOO_MANY_REQUESTS - rate limit exceeded
    - 403: Connector doesn't belong to user
    """
    import asyncio
    import logging

    from botbalance.exchanges.models import ExchangeAccount
    from botbalance.exchanges.portfolio_service import portfolio_service

    logger = logging.getLogger(__name__)

    try:
        # Validate request data
        request_serializer = RefreshStateRequestSerializer(data=request.data)
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

        connector_id = request_serializer.validated_data.get("connector_id")

        # Resolve exchange account
        if connector_id:
            # Validate connector belongs to user
            try:
                exchange_account = ExchangeAccount.objects.get(
                    id=connector_id, user=request.user
                )
            except ExchangeAccount.DoesNotExist:
                return Response(
                    {
                        "status": "error",
                        "message": "Exchange account not found or doesn't belong to you",
                        "error_code": "CONNECTOR_NOT_FOUND",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        else:
            # Auto-select user's active exchange account
            active_accounts = ExchangeAccount.objects.filter(
                user=request.user, is_active=True
            )

            if not active_accounts.exists():
                return Response(
                    {
                        "status": "error",
                        "message": "No active exchange accounts found",
                        "error_code": "NO_ACTIVE_CONNECTORS",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
            elif active_accounts.count() > 1:
                return Response(
                    {
                        "status": "error",
                        "message": f"Multiple active exchange accounts found ({active_accounts.count()}). Please specify connector_id parameter.",
                        "error_code": "MULTIPLE_ACTIVE_CONNECTORS",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            exchange_account = cast(
                "ExchangeAccount", active_accounts.first()
            )  # Guaranteed by count() == 1 check above

        # Refresh portfolio state
        portfolio_state, error_code = asyncio.run(
            portfolio_service.upsert_portfolio_state(exchange_account, source="manual")
        )

        if error_code:
            # Handle specific error cases
            if error_code == "NO_ACTIVE_STRATEGY":
                return Response(
                    {
                        "status": "error",
                        "message": "No active strategy found for connector",
                        "error_code": "NO_ACTIVE_STRATEGY",
                        "connector_id": exchange_account.id,
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            elif error_code == "ERROR_PRICING":
                return Response(
                    {
                        "status": "error",
                        "message": "Unable to get prices for some assets",
                        "error_code": "ERROR_PRICING",
                        "connector_id": exchange_account.id,
                        # TODO: Add missing_prices list from actual error
                    },
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            elif error_code == "TOO_MANY_REQUESTS":
                return Response(
                    {
                        "status": "error",
                        "message": "Rate limit exceeded. Please wait before requesting refresh again",
                        "error_code": "TOO_MANY_REQUESTS",
                        "retry_after_seconds": 5,
                        "connector_id": exchange_account.id,
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            else:
                # Generic error
                return Response(
                    {
                        "status": "error",
                        "message": "Failed to refresh portfolio state",
                        "error_code": error_code,
                        "connector_id": exchange_account.id,
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        # Success - return updated state
        if portfolio_state is None:  # Should not happen, but mypy check
            return Response(
                {
                    "status": "error",
                    "message": "Failed to create portfolio state",
                    "error_code": "INTERNAL_ERROR",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        state_data = portfolio_state.to_summary_dict()

        response_data = {
            "status": "success",
            "state": state_data,
        }

        serializer = RefreshStateResponseSerializer(data=response_data)
        if serializer.is_valid():
            nav_info = ""
            if portfolio_state:  # mypy safety check
                nav_info = (
                    f": NAV={portfolio_state.nav_quote} {portfolio_state.quote_asset}"
                )
            logger.info(
                f"Portfolio state refreshed for user {sanitize_for_logs(request.user.username)}, "
                f"connector {exchange_account.name}{nav_info}"
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
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
        logger = logging.getLogger(__name__)
        logger.error(f"Error in refresh_portfolio_state_view: {e}", exc_info=True)

        return Response(
            {
                "status": "error",
                "message": "Failed to refresh portfolio state due to an internal error",
                "error_code": "REFRESH_STATE_ERROR",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
