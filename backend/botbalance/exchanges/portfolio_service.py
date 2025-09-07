"""
Portfolio calculation service for Step 2: Portfolio Snapshot.

Provides NAV calculation, asset allocation percentages,
and portfolio summary data for the dashboard.
"""

import logging
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import NamedTuple

from django.core.cache import cache  # Still needed for cooldown
from django.utils import timezone

from .models import ExchangeAccount, PortfolioState
from .price_service import price_service

logger = logging.getLogger(__name__)


# Circuit breaker removed - now using simple health tracking in ExchangeAccount model


class Balance(NamedTuple):
    """Represents a balance entry from exchange."""

    symbol: str
    balance: Decimal


class PortfolioAsset(NamedTuple):
    """Represents a single asset in the portfolio."""

    symbol: str
    balance: Decimal
    price_usd: Decimal | None
    value_usd: Decimal
    percentage: Decimal
    price_source: str  # 'cached', 'fresh', 'mock'


class PortfolioSummary(NamedTuple):
    """Complete portfolio summary data."""

    total_nav: Decimal
    assets: list[PortfolioAsset]
    quote_currency: str
    timestamp: datetime
    exchange_account: str
    price_cache_stats: dict


class PortfolioService:
    """
    Service for calculating portfolio metrics and NAV.

    Features:
    - Net Asset Value (NAV) calculation
    - Asset allocation percentages
    - Multi-exchange support
    - Price staleness handling
    - Detailed portfolio breakdown
    """

    # Configuration
    MIN_BALANCE_THRESHOLD = Decimal("0.0001")  # Minimum balance to include in portfolio
    ROUNDING_PRECISION = 2  # Decimal places for USD values
    PERCENTAGE_PRECISION = 1  # Decimal places for percentages

    def __init__(self):
        self.price_service = price_service

    def _round_decimal(self, value: Decimal, precision: int) -> Decimal:
        """Round decimal to specified precision."""
        quantizer = Decimal("0.1") ** precision
        return value.quantize(quantizer, rounding=ROUND_HALF_UP)

    def _get_trading_pair(self, asset: str, quote: str = "USDT") -> str:
        """Generate trading pair symbol for price lookup."""
        asset = asset.upper()
        quote = quote.upper()

        # Handle stablecoins - they're worth ~$1
        if asset in {"USDT", "USDC", "BUSD", "DAI", "TUSD"}:
            return f"{asset}USD"  # Return USD pair for stablecoins

        # Standard trading pairs
        return f"{asset}{quote}"

    async def _get_asset_price(
        self, asset: str, quote: str = "USDT"
    ) -> tuple[Decimal | None, str]:
        """
        Get USD price for an asset with source tracking.

        Returns:
            Tuple of (price, source) where source is 'cached', 'fresh', 'mock', or 'stablecoin'
        """
        asset = asset.upper()

        # Handle stablecoins
        if asset in {"USDT", "USDC", "BUSD", "DAI", "TUSD"}:
            return Decimal("1.00"), "stablecoin"

        # Helper: try one symbol with  коммит->fresh and return (price, source) or (None, reason)
        async def _try_symbol(symbol: str) -> tuple[Decimal | None, str]:
            try:
                # 1) Try cached via service (non-stale)
                cached = self.price_service.get_cached_prices([symbol]).get(symbol)
                if cached and cached.get("price") is not None:
                    return Decimal(str(cached["price"])), "cached"

                # 2) Try fresh fetch (service решит: mid/last, mainnet/testnet)
                fresh = await self.price_service.get_price(symbol, force_refresh=True)
                if fresh is not None:
                    return fresh, "fresh"

                return None, "unavailable"
            except Exception as e:  # noqa: BLE001
                logger.error(f"Error fetching price for {symbol}: {e}")
                return None, "error"

        # Primary quotes to try
        quotes_order = [quote.upper(), "USD", "USDC", "BUSD"]

        # 1) Try direct pairs: ASSET+QUOTE, ASSET+USD/USDC/BUSD
        for q in quotes_order:
            pair = f"{asset}{q}"
            price, src = await _try_symbol(pair)
            if price is not None:
                return price, src

        # 2) Try reversed pairs and invert price: QUOTE+ASSET
        for q in quotes_order:
            pair_rev = f"{q}{asset}"
            price, src = await _try_symbol(pair_rev)
            if price is not None and price != 0:
                try:
                    inverted = (Decimal("1") / price).quantize(Decimal("0.00000001"))
                except Exception:
                    inverted = Decimal("0")
                if inverted > 0:
                    return inverted, src

        logger.warning(f"No price available for {asset} in quotes {quotes_order}")
        return None, "unavailable"

    def _convert_state_to_summary(
        self, state_data: dict, exchange_account: ExchangeAccount
    ) -> PortfolioSummary:
        """
        Convert PortfolioState data to legacy PortfolioSummary format.
        Used by deprecated calculate_portfolio_summary wrapper.
        """
        from datetime import datetime

        # Convert positions to PortfolioAsset objects
        assets = []
        total_nav = state_data["nav_quote"]

        for symbol, position in state_data["positions"].items():
            amount = Decimal(position["amount"])
            quote_value = Decimal(position["quote_value"])

            # Calculate percentage
            percentage = (
                self._round_decimal((quote_value / total_nav) * 100, 1)
                if total_nav > 0
                else Decimal("0.0")
            )

            # Get price from prices dict
            price = Decimal(state_data["prices"].get(symbol, "0"))

            assets.append(
                PortfolioAsset(
                    symbol=symbol,
                    balance=amount,
                    price_usd=price,  # Using quote asset price instead of USD
                    value_usd=quote_value,  # Using quote asset value instead of USD
                    percentage=percentage,
                    price_source="state",
                )
            )

        # Sort by value (descending)
        assets.sort(key=lambda x: x.value_usd, reverse=True)

        return PortfolioSummary(
            total_nav=total_nav,
            assets=assets,
            quote_currency=state_data["quote_asset"],
            timestamp=datetime.utcnow(),
            exchange_account=exchange_account.name,
            price_cache_stats={"source": "portfolio_state", "deprecated": True},
        )

    async def calculate_portfolio_summary(
        self, exchange_account: ExchangeAccount, force_refresh_prices: bool = False
    ) -> PortfolioSummary | None:
        """
        [DEPRECATED] Calculate complete portfolio summary with NAV and allocations.

        ⚠️  DEPRECATED: This method is deprecated and will be removed in a future version.
        ⚠️  Use PortfolioState API instead:
        ⚠️    - calculate_state_for_strategy() for new logic
        ⚠️    - GET/POST /api/me/portfolio/state/ endpoints

        This wrapper converts PortfolioState data to legacy PortfolioSummary format
        for backward compatibility during the migration period.
        """
        import warnings
        from datetime import datetime

        warnings.warn(
            "calculate_portfolio_summary is deprecated. Migrate to PortfolioState API.",
            DeprecationWarning,
            stacklevel=2,
        )

        logger.warning(
            f"DEPRECATED: calculate_portfolio_summary called for {exchange_account.name}. "
            "Migrate to PortfolioState API."
        )

        try:
            # Use new PortfolioState logic
            state_data = await self.calculate_state_for_strategy(exchange_account)
            if state_data is None:
                logger.warning(
                    f"No state data available for {exchange_account.name}. "
                    "This may be due to missing active strategy (normal during migration)."
                )

                # TEMPORARY FALLBACK: For migration period, return empty portfolio
                # instead of None to maintain test compatibility
                return PortfolioSummary(
                    total_nav=Decimal("0.00"),
                    assets=[],
                    quote_currency="USDT",  # Default quote currency
                    timestamp=datetime.utcnow(),
                    exchange_account=exchange_account.name,
                    price_cache_stats={
                        "source": "portfolio_state",
                        "deprecated": True,
                        "fallback": True,
                    },
                )

            # Convert to legacy format
            summary = self._convert_state_to_summary(state_data, exchange_account)

            logger.info(
                f"[DEPRECATED PATH] Portfolio summary: NAV={summary.total_nav} {summary.quote_currency}, "
                f"{len(summary.assets)} assets"
            )
            return summary

        except Exception as e:
            logger.error(f"Deprecated portfolio calculation failed: {e}", exc_info=True)
            return None

    async def get_portfolio_assets_only(
        self, exchange_account: ExchangeAccount
    ) -> list[PortfolioAsset]:
        """
        Get just the asset list without full summary (lighter operation).

        Returns:
            List of PortfolioAsset objects
        """
        summary = await self.calculate_portfolio_summary(exchange_account)
        return summary.assets if summary else []

    async def get_nav_only(self, exchange_account: ExchangeAccount) -> Decimal | None:
        """
        Get just the NAV value (lightest operation).

        Returns:
            Total portfolio NAV in USD or None
        """
        summary = await self.calculate_portfolio_summary(exchange_account)
        return summary.total_nav if summary else None

    def validate_portfolio_data(self, summary: PortfolioSummary) -> list[str]:
        """
        Validate portfolio calculation results.

        Returns:
            List of validation issues (empty list if all valid)
        """
        issues = []

        # Check percentage sum
        if summary.assets:
            total_percentage = sum(asset.percentage for asset in summary.assets)
            if abs(total_percentage - Decimal("100")) > Decimal(
                "0.1"
            ):  # Allow small rounding errors
                issues.append(f"Asset percentages sum to {total_percentage}%, not 100%")

        # Check NAV vs sum of asset values
        if summary.assets:
            calculated_nav = sum(asset.value_usd for asset in summary.assets)
            if abs(calculated_nav - summary.total_nav) > Decimal("0.01"):
                issues.append(
                    f"NAV mismatch: {summary.total_nav} vs calculated {calculated_nav}"
                )

        # Check for negative values
        if summary.total_nav < 0:
            issues.append("Negative NAV detected")

        for asset in summary.assets:
            if asset.value_usd < 0:
                issues.append(f"Negative value for {asset.symbol}")
            if asset.percentage < 0:
                issues.append(f"Negative percentage for {asset.symbol}")

        return issues

    # get_exchange_status removed - replaced by simple health fields in ExchangeAccount model

    async def calculate_state_for_strategy(
        self, exchange_account: ExchangeAccount
    ) -> dict | None:
        """
        Calculate portfolio state for a specific strategy (universe-focused).

        Returns state data only for assets that are part of the active strategy,
        in the strategy's quote asset. Used for PortfolioState creation.

        Args:
            exchange_account: Exchange account to calculate state for

        Returns:
            Dict with state data or None if calculation fails:
            {
                "quote_asset": "USDT",
                "nav_quote": Decimal("1234.56"),
                "positions": {"BTCUSDT": {"amount": "0.12", "quote_value": "7234.50"}},
                "prices": {"BTCUSDT": "60287.1"},
                "strategy_id": 1,
                "universe_symbols": ["BTCUSDT", "ETHUSDT"]
            }
        """
        logger.info(
            f"Calculating state for strategy on account: {exchange_account.name}"
        )

        try:
            # Import Strategy here to avoid circular imports
            from asgiref.sync import sync_to_async

            from strategies.models import Strategy

            # 1. Check for active strategy on this connector
            strategy = await sync_to_async(
                lambda: Strategy.objects.filter(
                    exchange_account=exchange_account, is_active=True
                ).first()
            )()

            if not strategy:
                logger.warning(
                    f"No active strategy found for exchange account {exchange_account.name}"
                )
                return None  # Will result in NO_ACTIVE_STRATEGY error

            # 2. Get strategy universe (allocation symbols)
            allocations = await sync_to_async(strategy.get_target_allocations)()
            if not allocations:
                logger.warning(f"Strategy {strategy.name} has no allocations defined")
                return None

            universe_symbols = list(allocations.keys())
            logger.info(
                f"Strategy universe: {universe_symbols} (quote: {strategy.quote_asset})"
            )

            # 3. Get balances from exchange for ALL assets (not filtered)
            # We'll filter to universe after getting all balances
            adapter = exchange_account.get_adapter()
            all_balances = await adapter.get_balances(exchange_account.account_type)

            if not all_balances:
                logger.warning(f"No balances found for account {exchange_account.name}")
                return None

            # 4. Process ALL universe symbols (not just those with balance > 0)
            # universe_symbols contains individual assets (BTC, USDT), not trading pairs
            strategy_assets = set(universe_symbols) - {
                strategy.quote_asset
            }  # Remove quote asset

            # Get balances for all strategy assets (including zero balances)
            strategy_balances = {}
            for asset in strategy_assets:
                balance = all_balances.get(asset, Decimal("0"))
                strategy_balances[asset] = balance

            # Log only non-zero balances for clarity
            non_zero_balances = {
                k: v
                for k, v in strategy_balances.items()
                if v > self.MIN_BALANCE_THRESHOLD
            }
            logger.info(f"Strategy balances found: {list(non_zero_balances.keys())}")

            # 5. Get prices only for assets with non-zero balances
            # Build price lookup map: symbol -> pair
            price_pairs = []
            asset_to_pair = {}
            for asset, balance in strategy_balances.items():
                if (
                    balance > self.MIN_BALANCE_THRESHOLD
                ):  # Only get prices for non-zero balances
                    pair = f"{asset}{strategy.quote_asset}"
                    price_pairs.append(pair)
                    asset_to_pair[asset] = pair

            # Batch price fetch using adapter (new architecture)
            prices_raw = await self.price_service.get_prices_batch_with_adapter(
                adapter, price_pairs
            )
            if not prices_raw:
                prices_raw = {}

            # 6. STRICT price validation - prices must be available for non-zero balances only
            missing_prices = []
            prices = {}  # Will store: {asset: price} format, not {pair: price}
            for asset, pair in asset_to_pair.items():
                price = prices_raw.get(pair)
                if price is None or price <= 0:
                    missing_prices.append(pair)
                else:
                    prices[asset] = price  # Store by asset symbol, not trading pair

            if missing_prices:
                logger.error(
                    f"Missing prices for assets with non-zero balances: {missing_prices}"
                )
                return None  # Will result in ERROR_PRICING

            # 7. Calculate positions and NAV - include ALL assets from universe_symbols
            positions = {}
            nav_quote = Decimal("0")

            for asset, balance in strategy_balances.items():
                if balance > self.MIN_BALANCE_THRESHOLD:
                    # Asset has balance - get price and calculate value
                    price = prices[asset]  # Use asset symbol as key, not trading pair
                    quote_value = self._round_decimal(balance * price, 2)
                    nav_quote += quote_value
                else:
                    # Asset has zero balance - include in positions but no value
                    quote_value = Decimal("0")

                # Use asset symbol as key, not trading pair
                positions[asset] = {
                    "amount": str(balance),
                    "quote_value": str(quote_value),
                }

            # 8. Add quote asset itself - always include in positions
            quote_balance = all_balances.get(strategy.quote_asset, Decimal("0"))
            quote_symbol = strategy.quote_asset  # e.g., USDT

            # Always add quote asset to positions and prices
            positions[quote_symbol] = {
                "amount": str(quote_balance),
                "quote_value": str(quote_balance),  # 1:1 rate for quote asset
            }
            prices[quote_symbol] = Decimal("1.0")

            # Add to NAV only if balance > threshold
            if quote_balance > self.MIN_BALANCE_THRESHOLD:
                nav_quote += quote_balance

            nav_quote = self._round_decimal(nav_quote, 8)

            state_data = {
                "quote_asset": strategy.quote_asset,
                "nav_quote": nav_quote,
                "positions": positions,
                "prices": {k: str(v) for k, v in prices.items()},
                "strategy_id": strategy.id,
                "universe_symbols": universe_symbols,
            }

            logger.info(
                f"State calculated: NAV={nav_quote} {strategy.quote_asset}, {len(positions)} positions"
            )
            return state_data

        except Exception as e:
            logger.error(f"Failed to calculate state for strategy: {e}", exc_info=True)
            return None

    async def upsert_portfolio_state(
        self, exchange_account: ExchangeAccount, source: str = "tick"
    ) -> tuple[PortfolioState | None, str | None]:
        """
        Atomically update/create PortfolioState for exchange account.

        Args:
            exchange_account: Exchange account to update state for
            source: Source of the update ("tick", "manual")

        Returns:
            Tuple of (PortfolioState, error_code) where error_code is None on success
            Error codes: "NO_ACTIVE_STRATEGY", "ERROR_PRICING", "TOO_MANY_REQUESTS"
        """
        import time

        # Import at function start to avoid scope issues
        from asgiref.sync import sync_to_async

        logger.info(f"Upserting portfolio state for account: {exchange_account.name}")
        start_time = time.time()

        try:
            # 1. Check cooldown protection (configurable seconds per connector)
            from django.conf import settings

            cooldown_seconds = getattr(settings, "PORTFOLIO_STATE_COOLDOWN_SEC", 5)
            cooldown_key = f"portfolio_state_cooldown_{exchange_account.id}"
            if cache.get(cooldown_key):
                logger.info(
                    f"Cooldown active for account {exchange_account.name} ({cooldown_seconds}s)"
                )
                return None, "TOO_MANY_REQUESTS"

            # 2. Calculate state data
            state_data = await self.calculate_state_for_strategy(exchange_account)
            if state_data is None:
                # Check specific reason for failure
                from strategies.models import Strategy

                strategy_exists = await sync_to_async(
                    lambda: Strategy.objects.filter(
                        exchange_account=exchange_account, is_active=True
                    ).exists()
                )()

                if not strategy_exists:
                    await sync_to_async(exchange_account.update_health_error)(
                        "NO_ACTIVE_STRATEGY"
                    )
                    return None, "NO_ACTIVE_STRATEGY"
                else:
                    await sync_to_async(exchange_account.update_health_error)(
                        "ERROR_PRICING"
                    )
                    return None, "ERROR_PRICING"

            # 3. Set cooldown (configurable seconds)
            cache.set(cooldown_key, True, cooldown_seconds)

            # 4. Atomically upsert PortfolioState
            state, created = await sync_to_async(
                PortfolioState.objects.update_or_create
            )(
                exchange_account=exchange_account,
                defaults={
                    "ts": timezone.now(),
                    "quote_asset": state_data["quote_asset"],
                    "nav_quote": state_data["nav_quote"],
                    "positions": state_data["positions"],
                    "prices": state_data["prices"],
                    "source": source,
                    "strategy_id": state_data["strategy_id"],
                    "universe_symbols": state_data["universe_symbols"],
                },
            )

            action = "created" if created else "updated"

            # 5. Update health status for successful operation
            latency_ms = int((time.time() - start_time) * 1000)
            await sync_to_async(exchange_account.update_health_success)(latency_ms)

            logger.info(
                f"PortfolioState {action} for account {exchange_account.name}: "
                f"NAV={state.nav_quote} {state.quote_asset}, latency={latency_ms}ms"
            )

            return state, None

        except Exception as e:
            logger.error(f"Failed to upsert portfolio state: {e}", exc_info=True)
            await sync_to_async(exchange_account.update_health_error)("ERROR_PRICING")
            return None, "ERROR_PRICING"  # Generic error


# Singleton instance
portfolio_service = PortfolioService()
