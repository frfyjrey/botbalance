"""
Portfolio snapshot service for Step 2.

Provides functionality to create and manage portfolio snapshots,
including throttling to prevent excessive snapshot creation.
"""

import logging
from decimal import Decimal
from typing import NamedTuple

import redis
from django.conf import settings
from django.contrib.auth.models import User

from .models import ExchangeAccount, PortfolioSnapshot
from .portfolio_service import portfolio_service


def sanitize_for_logs(text: str) -> str:
    """
    Sanitize text for safe logging by removing control characters.

    Prevents log injection attacks by removing newlines and carriage returns.
    """
    if not text:
        return ""
    return str(text).replace("\r\n", "").replace("\n", "").replace("\r", "")


logger = logging.getLogger(__name__)


class SnapshotData(NamedTuple):
    """Data structure for snapshot creation."""

    nav_quote: Decimal
    positions: dict[str, dict[str, str]]  # {asset: {amount: str, quote_value: str}}
    prices: dict[str, Decimal]  # {symbol: price}
    quote_asset: str


class SnapshotService:
    """
    Service for creating and managing portfolio snapshots.

    Handles snapshot creation with Redis-based throttling to prevent
    excessive writes from UI requests.
    """

    # Redis key prefix for throttling locks
    THROTTLE_KEY_PREFIX = "snapshot:lock"

    # Default throttle TTL (60 seconds)
    DEFAULT_THROTTLE_TTL = 60

    def __init__(self):
        """Initialize snapshot service with Redis connection."""
        self.redis_client = redis.Redis.from_url(
            getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        )

    async def create_snapshot(
        self,
        user: User,
        exchange_account: ExchangeAccount | None,
        source: str,
        strategy_version: int | None = None,
        force: bool = False,
    ) -> PortfolioSnapshot | None:
        """
        Create a portfolio snapshot for the user.

        Args:
            user: User to create snapshot for
            exchange_account: Exchange account (can be None if user has no accounts)
            source: How this snapshot was created (summary/order_fill/cron/init)
            strategy_version: Version of strategy when snapshot was taken (optional)
            force: Bypass throttling if True

        Returns:
            Created PortfolioSnapshot or None if failed
        """
        try:
            logger.info(
                f"Creating {source} snapshot for user {sanitize_for_logs(user.username)}, "
                f"account: {exchange_account.name if exchange_account else 'None'}"
            )

            # If no exchange account, we can't calculate portfolio
            if not exchange_account:
                logger.warning(
                    f"User {sanitize_for_logs(user.username)} has no active exchange account, cannot create snapshot"
                )
                return None

            # Calculate portfolio data
            portfolio_summary = await portfolio_service.calculate_portfolio_summary(
                exchange_account,
                force_refresh_prices=(source in ["order_fill", "cron"]),
            )

            if not portfolio_summary:
                logger.error(
                    f"Failed to calculate portfolio summary for user {sanitize_for_logs(user.username)}"
                )
                return None

            # Prepare snapshot data
            snapshot_data = self._prepare_snapshot_data(portfolio_summary)

            # Create snapshot (use sync_to_async for Django ORM in async context)
            from asgiref.sync import sync_to_async

            @sync_to_async
            def create_snapshot_sync():
                return PortfolioSnapshot.objects.create(
                    user=user,
                    exchange_account=exchange_account,
                    quote_asset=snapshot_data.quote_asset,
                    nav_quote=snapshot_data.nav_quote,
                    positions=snapshot_data.positions,
                    prices={k: str(v) for k, v in snapshot_data.prices.items()},
                    source=source,
                    strategy_version=strategy_version,
                )

            snapshot = await create_snapshot_sync()

            logger.info(
                f"Created snapshot {snapshot.id} for user {sanitize_for_logs(user.username)}: "
                f"NAV={snapshot.nav_quote} {snapshot.quote_asset}, "
                f"assets={snapshot.get_asset_count()}"
            )

            return snapshot

        except Exception as e:
            logger.error(
                f"Failed to create snapshot for user {sanitize_for_logs(user.username)}: {e}",
                exc_info=True,
            )
            return None

    async def throttled_create_snapshot(
        self,
        user: User,
        exchange_account: ExchangeAccount | None,
        source: str = "summary",
        ttl: int | None = None,
    ) -> PortfolioSnapshot | None:
        """
        Create snapshot with Redis-based throttling.

        Only creates snapshot if no recent snapshot was created for this user.
        Used for UI-triggered snapshots to prevent spam.

        Args:
            user: User to create snapshot for
            exchange_account: Exchange account
            source: Snapshot source (defaults to "summary")
            ttl: Throttle TTL in seconds (defaults to DEFAULT_THROTTLE_TTL)

        Returns:
            Created PortfolioSnapshot or None if throttled/failed
        """
        if ttl is None:
            ttl = self.DEFAULT_THROTTLE_TTL

        throttle_key = f"{self.THROTTLE_KEY_PREFIX}:{user.id}"

        try:
            # Try to acquire throttle lock
            if not self.redis_client.set(throttle_key, "1", nx=True, ex=ttl):
                logger.info(
                    f"Snapshot creation for user {sanitize_for_logs(user.username)} throttled "
                    f"(recent snapshot within {ttl}s)"
                )
                return None

            # Create snapshot
            return await self.create_snapshot(
                user=user,
                exchange_account=exchange_account,
                source=source,
            )

        except redis.RedisError as e:
            # If Redis is unavailable, still create snapshot (fail open)
            logger.warning(
                f"Redis unavailable for throttling user {sanitize_for_logs(user.username)}: {e}. Creating snapshot anyway."
            )
            return await self.create_snapshot(
                user=user,
                exchange_account=exchange_account,
                source=source,
            )

    def _prepare_snapshot_data(self, portfolio_summary) -> SnapshotData:
        """
        Convert portfolio summary to snapshot data format.

        Args:
            portfolio_summary: PortfolioSummary from portfolio_service

        Returns:
            SnapshotData ready for database storage
        """
        # Convert assets to positions format
        positions = {}
        prices = {}

        for asset in portfolio_summary.assets:
            positions[asset.symbol] = {
                "amount": str(asset.balance),
                "quote_value": str(asset.value_usd),
            }

            # Build price symbol (asset + quote)
            if asset.symbol != portfolio_summary.quote_currency:
                price_symbol = f"{asset.symbol}{portfolio_summary.quote_currency}"
                prices[price_symbol] = asset.price_usd

        return SnapshotData(
            nav_quote=portfolio_summary.total_nav,
            positions=positions,
            prices=prices,
            quote_asset=portfolio_summary.quote_currency,
        )

    def get_recent_snapshots(
        self,
        user: User,
        limit: int = 10,
        exchange_account: ExchangeAccount | None = None,
    ) -> list[PortfolioSnapshot]:
        """
        Get recent snapshots for user.

        Args:
            user: User to get snapshots for
            limit: Maximum number of snapshots to return
            exchange_account: Filter by exchange account (optional)

        Returns:
            List of recent snapshots ordered by timestamp desc
        """
        queryset = PortfolioSnapshot.objects.filter(user=user).select_related(
            "exchange_account"
        )

        if exchange_account:
            queryset = queryset.filter(exchange_account=exchange_account)

        return list(queryset.order_by("-ts")[:limit])

    def get_latest_snapshot(
        self,
        user: User,
        exchange_account: ExchangeAccount | None = None,
    ) -> PortfolioSnapshot | None:
        """
        Get the most recent snapshot for user.

        Args:
            user: User to get snapshot for
            exchange_account: Filter by exchange account (optional)

        Returns:
            Latest snapshot or None if no snapshots exist
        """
        snapshots = self.get_recent_snapshots(
            user=user, limit=1, exchange_account=exchange_account
        )
        return snapshots[0] if snapshots else None

    def cleanup_old_snapshots(
        self, days_to_keep: int = 90, batch_size: int = 1000
    ) -> int:
        """
        Clean up old snapshots beyond retention period.

        Args:
            days_to_keep: Number of days of snapshots to keep
            batch_size: Number of snapshots to delete per batch

        Returns:
            Number of snapshots deleted
        """
        from datetime import timedelta

        from django.utils import timezone

        cutoff_date = timezone.now() - timedelta(days=days_to_keep)

        # Get old snapshots to delete
        old_snapshots = PortfolioSnapshot.objects.filter(
            ts__lt=cutoff_date
        ).values_list("id", flat=True)[:batch_size]

        if not old_snapshots:
            return 0

        # Delete in batches
        deleted_count = PortfolioSnapshot.objects.filter(
            id__in=list(old_snapshots)
        ).delete()[0]

        logger.info(
            f"Cleaned up {deleted_count} portfolio snapshots older than {days_to_keep} days"
        )

        return deleted_count


# Global service instance
snapshot_service = SnapshotService()
